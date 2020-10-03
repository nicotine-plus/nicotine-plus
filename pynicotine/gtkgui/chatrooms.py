# COPYRIGHT (C) 2020 Nicotine+ Team
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016 Mutnick <muhing@yahoo.com>
# COPYRIGHT (C) 2008-2011 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2006-2009 Daelstorm <daelstorm@gmail.com>
# COPYRIGHT (C) 2007 Gallows <g4ll0ws@gmail.com>
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
from collections import deque
from gettext import gettext as _
from os.path import commonprefix

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk
from gi.repository import Pango as pango

from pynicotine import slskmessages
from pynicotine.gtkgui import nowplaying
from pynicotine.gtkgui.dialogs import EntryDialog
from pynicotine.gtkgui.roomwall import RoomWall
from pynicotine.gtkgui.roomwall import Tickers
from pynicotine.gtkgui.utils import AppendLine
from pynicotine.gtkgui.utils import HideColumns
from pynicotine.gtkgui.utils import Humanize
from pynicotine.gtkgui.utils import HumanSpeed
from pynicotine.gtkgui.utils import IconNotebook
from pynicotine.gtkgui.utils import InitialiseColumns
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.gtkgui.utils import PressHeader
from pynicotine.gtkgui.utils import ScrollBottom
from pynicotine.gtkgui.utils import TextSearchBar
from pynicotine.gtkgui.utils import expand_alias
from pynicotine.gtkgui.utils import is_alias
from pynicotine.gtkgui.utils import showCountryTooltip
from pynicotine.logfacility import log
from pynicotine.utils import CleanFile
from pynicotine.utils import cmp
from pynicotine.utils import write_log


def GetCompletion(part, list):
    matches = GetCompletions(part, list)
    if len(matches) == 0:
        return None, 0
    if len(matches) == 1:
        return matches[0], 1
    else:
        return commonprefix([x.lower() for x in matches]), 0


def GetCompletions(part, list):
    lowerpart = part.lower()
    matches = [x for x in set(list) if x.lower().startswith(lowerpart) and len(x) >= len(part)]
    return matches


class RoomsControl:

    CMDS = {
        "/alias ", "/unalias ", "/whois ", "/browse ", "/ip ", "/pm ", "/msg ", "/search ",
        "/usearch ", "/rsearch ", "/bsearch ", "/join ", "/leave ", "/add ", "/buddy ", "/rem ",
        "/unbuddy ", "/ban ", "/ignore ", "/ignoreip ", "/unban ", "/unignore ", "/clear ",
        "/part ", "/quit ", "/exit ", "/rescan ", "/tick ", "/info ", "/toggle", "/tickers"
    }

    def __init__(self, ChatNotebook):

        self.frame = ChatNotebook.frame
        self.ChatNotebook = ChatNotebook

        self.joinedrooms = {}
        self.autojoin = 1
        self.rooms = []
        config = self.frame.np.config.sections
        self.PrivateRooms = config["private_rooms"]["rooms"]

        # Config cleanup
        for room, data in self.PrivateRooms.items():
            if "owner" not in data:
                self.PrivateRooms[room]["owner"] = None
            if "operator" in data:
                del self.PrivateRooms[room]["operator"]

        self.clist = []
        self.roomsmodel = gtk.ListStore(str, int, int)
        self.frame.roomlist.RoomsList.set_model(self.roomsmodel)

        self.cols = InitialiseColumns(
            self.frame.roomlist.RoomsList,
            [_("Room"), 180, "text", self.RoomStatus],
            [_("Users"), 0, "number", self.RoomStatus]
        )
        self.cols[0].set_sort_column_id(0)
        self.cols[1].set_sort_column_id(1)

        self.roomsmodel.set_sort_func(1, self.PrivateRoomsSort, 1)

        for i in range(2):
            parent = self.cols[i].get_widget().get_ancestor(gtk.Button)
            if parent:
                parent.connect('button_press_event', PressHeader)

        self.popup_room = None
        self.popup_menu = PopupMenu(self.frame).setup(
            ("#" + _("Join Room"), self.OnPopupJoin),
            ("#" + _("Leave Room"), self.OnPopupLeave),
            ("#" + _("Create Room"), self.OnPopupCreatePublicRoom),
            ("", None),
            ("#" + _("Create Private Room"), self.OnPopupCreatePrivateRoom),
            ("#" + _("Disown Private Room"), self.OnPopupPrivateRoomDisown),
            ("#" + _("Cancel Room Membership"), self.OnPopupPrivateRoomDismember),
            ("", None),
            ("#" + _("Join Public Room"), self.OnJoinPublicRoom),
            ("", None),
            ("#" + _("Refresh"), self.OnPopupRefresh)
        )

        items = self.popup_menu.get_children()
        self.Menu_Join, self.Menu_Leave, self.Menu_Create_Room, self.Menu_Empty1, self.Menu_PrivateRoom_Create, self.Menu_PrivateRoom_Disown, self.Menu_PrivateRoom_Dismember, self.Menu_Empty2, self.Menu_JoinPublicRoom, self.Menu_Empty3, self.Menu_Refresh = items

        self.frame.roomlist.RoomsList.connect("button_press_event", self.OnListClicked)
        self.frame.roomlist.RoomsList.set_headers_clickable(True)

        self.ChatNotebook.Notebook.connect("switch-page", self.OnSwitchPage)
        self.ChatNotebook.Notebook.connect("page-reordered", self.OnReorderedPage)

        self.frame.SetTextBG(self.frame.roomlist.SearchRooms)

    def IsPrivateRoomOwned(self, room):

        if room in self.PrivateRooms:
            if self.PrivateRooms[room]["owner"] == self.frame.np.config.sections["server"]["login"]:
                return True

        return False

    def IsPrivateRoomMember(self, room):

        if room in self.PrivateRooms:
            return True

        return False

    def IsPrivateRoomOperator(self, room):

        if room in self.PrivateRooms:
            if self.frame.np.config.sections["server"]["login"] in self.PrivateRooms[room]["operators"]:
                return True

        return False

    def PrivateRoomsSort(self, model, iter1, iter2, column):

        try:
            private1 = model.get_value(iter1, 2) * 10000
            private1 += model.get_value(iter1, 1)
        except Exception:
            private1 = 0

        try:
            private2 = model.get_value(iter2, 2) * 10000
            private2 += model.get_value(iter2, 1)
        except Exception:
            private2 = 0

        return cmp(private1, private2)

    def RoomStatus(self, column, cellrenderer, model, iter, dummy='dummy'):
        if self.roomsmodel.get_value(iter, 2) >= 2:
            cellrenderer.set_property("underline", pango.Underline.SINGLE)
            cellrenderer.set_property("weight", pango.Weight.BOLD)
        elif self.roomsmodel.get_value(iter, 2) >= 1:
            cellrenderer.set_property("weight", pango.Weight.BOLD)
            cellrenderer.set_property("underline", pango.Underline.NONE)
        else:
            cellrenderer.set_property("weight", pango.Weight.NORMAL)
            cellrenderer.set_property("underline", pango.Underline.NONE)

        self.frame.CellDataFunc(column, cellrenderer, model, iter)

    def OnReorderedPage(self, notebook, page, page_num, force=0):

        room_tab_order = {}

        # Find position of opened autojoined rooms
        for name, room in self.joinedrooms.items():

            if name not in self.frame.np.config.sections["server"]["autojoin"]:
                continue

            room_tab_order[notebook.page_num(room.Main)] = name

        pos = 1000

        # Add closed autojoined rooms as well
        for name in self.frame.np.config.sections["server"]["autojoin"]:
            if name not in self.joinedrooms:
                room_tab_order[pos] = name
                pos += 1

        # Sort by "position"
        rto = list(room_tab_order.keys())
        rto.sort()
        new_autojoin = []
        for roomplace in rto:
            new_autojoin.append(room_tab_order[roomplace])

        # Save
        self.frame.np.config.sections["server"]["autojoin"] = new_autojoin

    def OnSwitchPage(self, notebook, page, page_num, force=0):

        if self.frame.MainNotebook.get_current_page() != self.frame.MainNotebook.page_num(self.frame.chathbox) and not force:
            return

        for name, room in self.joinedrooms.items():
            if room.Main == page:
                GLib.idle_add(room.ChatEntry.grab_focus)

                # Remove hilite
                self.frame.notifications.Clear("rooms", None, name)

    def ClearNotifications(self):

        if self.frame.MainNotebook.get_current_page() != self.frame.MainNotebook.page_num(self.frame.chathbox):
            return

        page = self.ChatNotebook.get_nth_page(self.ChatNotebook.get_current_page())

        for name, room in self.joinedrooms.items():
            if room.Main == page:
                # Remove hilite
                self.frame.notifications.Clear("rooms", None, name)

    def Focused(self, page, focused):

        if not focused:
            return

        for name, room in self.users.items():
            if room.Main == page:
                self.frame.notifications.Clear("rooms", name)

    def OnListClicked(self, widget, event):

        if event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:

            d = self.frame.roomlist.RoomsList.get_path_at_pos(int(event.x), int(event.y))
            if d:
                path, column, x, y = d
                room = self.roomsmodel.get_value(self.roomsmodel.get_iter(path), 0)
                if room not in self.joinedrooms:
                    self.frame.np.queue.put(slskmessages.JoinRoom(room))

            return True
        elif event.button == 3:
            return self.OnPopupMenu(widget, event)

        return False

    def OnPopupMenu(self, widget, event):

        if event.button != 3 or self.roomsmodel is None:
            return

        d = self.frame.roomlist.RoomsList.get_path_at_pos(int(event.x), int(event.y))

        if d:
            path, column, x, y = d
            room = self.roomsmodel.get_value(self.roomsmodel.get_iter(path), 0)

            if room in self.joinedrooms:
                act = (False, True)
            else:
                act = (True, False)
        else:
            room = None
            act = (False, False)

        self.popup_room = room
        prooms_enabled = True

        self.Menu_Join.set_sensitive(act[0])
        self.Menu_Leave.set_sensitive(act[1])

        self.Menu_PrivateRoom_Disown.set_sensitive(self.IsPrivateRoomOwned(self.popup_room))  # Disown
        self.Menu_PrivateRoom_Dismember.set_sensitive((prooms_enabled and self.IsPrivateRoomMember(self.popup_room)))  # Dismember

        self.popup_menu.popup(None, None, None, None, event.button, event.time)

    def OnPopupJoin(self, widget):
        self.frame.np.queue.put(slskmessages.JoinRoom(self.popup_room))

    def OnPopupCreatePublicRoom(self, widget):

        room = EntryDialog(
            self.frame.MainWindow,
            title=_("Create Public Room"),
            message=_('Enter the name of the public room you wish to create')
        )

        if room:
            self.frame.np.queue.put(slskmessages.JoinRoom(room))

    def OnJoinPublicRoom(self, widget):

        # Everything but queue.put shouldn't be here, but the server doesn't send a confirmation when joining
        # public room. It would be clearer if we faked such a message ourself somewhere in the core
        if 'Public ' in self.joinedrooms:
            return

        room = ChatRoom(self, 'Public ', {}, meta=True)
        self.joinedrooms['Public '] = room
        angle = 0

        try:
            angle = int(self.frame.np.config.sections["ui"]["labelrooms"])
        except Exception as e:
            print(e)

        self.ChatNotebook.append_page(room.Main, 'Public ', room.OnLeave, angle)

        room.CountUsers()

        self.frame.np.queue.put(slskmessages.JoinPublicRoom())

    def OnPopupCreatePrivateRoom(self, widget):

        room = EntryDialog(
            self.frame.MainWindow,
            title=_("Create Private Room"),
            message=_('Enter the name of the private room you wish to create')
        )

        if room:
            self.frame.np.queue.put(slskmessages.JoinRoom(room, 1))

    def OnPopupPrivateRoomDisown(self, widget):

        if self.IsPrivateRoomOwned(self.popup_room):
            self.frame.np.queue.put(slskmessages.PrivateRoomDisown(self.popup_room))
            del self.PrivateRooms[self.popup_room]
            self.SetPrivateRooms()

    def OnPopupPrivateRoomDismember(self, widget):

        if self.IsPrivateRoomMember(self.popup_room):
            self.frame.np.queue.put(slskmessages.PrivateRoomDismember(self.popup_room))
            del self.PrivateRooms[self.popup_room]
            self.SetPrivateRooms()

    def OnPopupLeave(self, widget):
        self.frame.np.queue.put(slskmessages.LeaveRoom(self.popup_room))

    def OnPopupRefresh(self, widget):
        self.frame.np.queue.put(slskmessages.RoomList())

    def JoinRoom(self, msg):

        if msg.room in self.joinedrooms:
            self.joinedrooms[msg.room].Rejoined(msg.users)
            return

        tab = ChatRoom(self, msg.room, msg.users)

        self.joinedrooms[msg.room] = tab

        if msg.private is not None:
            self.CreatePrivateRoom(msg.room, msg.owner, msg.operators)

        angle = 0
        try:
            angle = int(self.frame.np.config.sections["ui"]["labelrooms"])
        except Exception as e:
            print(e)

        self.ChatNotebook.append_page(tab.Main, msg.room, tab.OnLeave, angle)

        self.frame.searchroomslist[msg.room] = self.frame.RoomSearchCombo_List.append([(msg.room)])

        tab.CountUsers()

    def SetRoomList(self, msg):

        if self.autojoin:

            self.autojoin = 0
            if self.joinedrooms:
                room_list = list(self.joinedrooms.keys())
            else:
                room_list = self.frame.np.config.sections["server"]["autojoin"]

            for room in room_list:
                if room == 'Public ':
                    self.OnJoinPublicRoom(None)
                else:
                    self.frame.np.queue.put(slskmessages.JoinRoom(room))

        self.roomsmodel.clear()
        self.frame.roomlist.RoomsList.set_model(None)
        self.roomsmodel.set_default_sort_func(lambda *args: -1)
        self.roomsmodel.set_sort_func(1, lambda *args: -1)
        self.roomsmodel.set_sort_column_id(-1, gtk.SortType.ASCENDING)

        self.rooms = []
        for room, users in msg.rooms:
            self.roomsmodel.append([room, users, 0])
            self.rooms.append(room)

        self.SetPrivateRooms(msg.ownedprivaterooms, msg.otherprivaterooms)
        self.frame.roomlist.RoomsList.set_model(self.roomsmodel)
        self.roomsmodel.set_sort_func(1, self.PrivateRoomsSort, 1)
        self.roomsmodel.set_sort_column_id(1, gtk.SortType.DESCENDING)
        self.roomsmodel.set_default_sort_func(self.PrivateRoomsSort)

        if self.frame.np.config.sections["words"]["roomnames"]:
            self.frame.chatrooms.roomsctrl.UpdateCompletions()
            self.frame.privatechats.UpdateCompletions()

    def SetPrivateRooms(self, ownedrooms=[], otherrooms=[]):

        myusername = self.frame.np.config.sections["server"]["login"]

        for room in ownedrooms:
            try:
                self.PrivateRooms[room[0]]['joined'] = room[1]
                if self.PrivateRooms[room[0]]['owner'] != myusername:
                    log.add_warning(_("I remember the room %(room)s being owned by %(previous)s, but the server says its owned by %(new)s."), {
                        'room': room[0],
                        'previous': self.PrivateRooms[room[0]]['owner'],
                        'new': myusername
                    })
                self.PrivateRooms[room[0]]['owner'] = myusername
            except KeyError:
                self.PrivateRooms[room[0]] = {"users": [], "joined": room[1], "operators": [], "owner": myusername}

        for room in otherrooms:
            try:
                self.PrivateRooms[room[0]]['joined'] = room[1]
                if self.PrivateRooms[room[0]]['owner'] == myusername:
                    log.add_warning(_("I remember the room %(room)s being owned by %(old)s, but the server says that's not true."), {
                        'room': room[0],
                        'old': self.PrivateRooms[room[0]]['owner'],
                    })
                    self.PrivateRooms[room[0]]['owner'] = None
            except KeyError:
                self.PrivateRooms[room[0]] = {"users": [], "joined": room[1], "operators": [], "owner": None}

        iter = self.roomsmodel.get_iter_first()
        while iter is not None:
            room = self.roomsmodel.get_value(iter, 0)
            lastiter = iter
            iter = self.roomsmodel.iter_next(iter)
            if self.IsPrivateRoomOwned(room) or self.IsPrivateRoomMember(room):
                self.roomsmodel.remove(lastiter)

        for room in self.PrivateRooms:

            num = self.PrivateRooms[room]["joined"]

            if self.IsPrivateRoomOwned(room):
                self.roomsmodel.prepend([room, num, 2])
            elif self.IsPrivateRoomMember(room):
                self.roomsmodel.prepend([room, num, 1])

    def CreatePrivateRoom(self, room, owner=None, operators=[]):

        if room in self.PrivateRooms:
            if operators is not None:
                for operator in operators:
                    if operator not in self.PrivateRooms[room]["operators"]:
                        self.PrivateRooms[room]["operators"].append(operator)

            self.PrivateRooms[room]["owner"] = owner

            return

        self.PrivateRooms[room] = {"users": [], "joined": 0, "operators": operators, "owned": False, "owner": owner}

    def PrivateRoomUsers(self, msg):

        rooms = self.PrivateRooms

        if msg.room not in rooms:
            self.CreatePrivateRoom(msg.room)
            rooms[msg.room]["users"] = msg.users
            rooms[msg.room]["joined"] = msg.numusers
        else:
            rooms[msg.room]["users"] = msg.users
            rooms[msg.room]["joined"] = msg.numusers

        self.SetPrivateRooms()

    def PrivateRoomOwned(self, msg):

        rooms = self.PrivateRooms

        if msg.room not in rooms:
            self.CreatePrivateRoom(msg.room)
            rooms[msg.room]["operators"] = msg.operators
        else:
            rooms[msg.room]["operators"] = msg.operators

        self.SetPrivateRooms()

    def PrivateRoomAddUser(self, msg):

        rooms = self.PrivateRooms

        if msg.room in rooms:
            if msg.user not in rooms[msg.room]["users"]:
                rooms[msg.room]["users"].append(msg.user)

        self.SetPrivateRooms()

    def PrivateRoomRemoveUser(self, msg):

        rooms = self.PrivateRooms

        if msg.room in rooms:
            if msg.user in rooms[msg.room]["users"]:
                rooms[msg.room]["users"].remove(msg.user)

        self.SetPrivateRooms()

    def PrivateRoomOperatorAdded(self, msg):

        rooms = self.PrivateRooms

        if msg.room in rooms:
            if self.frame.np.config.sections["server"]["login"] not in rooms[msg.room]["operators"]:
                rooms[msg.room]["operators"].append(self.frame.np.config.sections["server"]["login"])

        self.SetPrivateRooms()

    def PrivateRoomOperatorRemoved(self, msg):

        rooms = self.PrivateRooms

        if msg.room in rooms:
            if self.frame.np.config.sections["server"]["login"] in rooms[msg.room]["operators"]:
                rooms[msg.room]["operators"].remove(self.frame.np.config.sections["server"]["login"])

        self.SetPrivateRooms()

    def PrivateRoomAddOperator(self, msg):

        rooms = self.PrivateRooms

        if msg.room in rooms:
            if msg.user not in rooms[msg.room]["operators"]:
                rooms[msg.room]["operators"].append(msg.user)

        self.SetPrivateRooms()

    def PrivateRoomRemoveOperator(self, msg):

        rooms = self.PrivateRooms

        if msg.room in rooms:
            if msg.user in rooms[msg.room]["operators"]:
                rooms[msg.room]["operators"].remove(msg.user)

        self.SetPrivateRooms()

    def PrivateRoomAdded(self, msg):

        rooms = self.PrivateRooms
        room = msg.room

        if room not in rooms:
            self.CreatePrivateRoom(room)
            log.add(_("You have been added to a private room: %(room)s"), {"room": room})

        self.SetPrivateRooms()

    def PrivateRoomRemoved(self, msg):

        rooms = self.PrivateRooms

        if msg.room in rooms:
            del rooms[msg.room]

        self.SetPrivateRooms()

    def TogglePrivateRooms(self, enabled):

        self.frame.np.config.sections["server"]["private_chatrooms"] = enabled

    def PrivateRoomDisown(self, msg):
        if msg.room in self.PrivateRooms:
            if self.PrivateRooms[msg.room]["owner"] == self.frame.np.config.sections["server"]["login"]:
                self.PrivateRooms[msg.room]["owner"] = None

    def GetUserStats(self, msg):
        for room in self.joinedrooms.values():
            room.GetUserStats(msg.user, msg.avgspeed, msg.files)

    def GetUserStatus(self, msg):
        for room in self.joinedrooms.values():
            room.GetUserStatus(msg.user, msg.status)

    def SetUserFlag(self, user, flag):
        for room in self.joinedrooms.values():
            room.SetUserFlag(user, flag)

    def GetUserAddress(self, user):

        if user not in self.frame.np.users or self.frame.np.users[user].addr is None:
            self.frame.np.queue.put(slskmessages.GetPeerAddress(user))

    def UserJoinedRoom(self, msg):

        if msg.room in self.joinedrooms:
            self.joinedrooms[msg.room].UserJoinedRoom(msg.username, msg.userdata)
            self.GetUserAddress(msg.username)

    def UserLeftRoom(self, msg):
        self.joinedrooms[msg.room].UserLeftRoom(msg.username)

    def TickerSet(self, msg):
        self.joinedrooms[msg.room].TickerSet(msg)

    def TickerAdd(self, msg):
        self.joinedrooms[msg.room].TickerAdd(msg)

    def TickerRemove(self, msg):
        self.joinedrooms[msg.room].TickerRemove(msg)

    def SayChatRoom(self, msg, text):
        if msg.user in self.frame.np.config.sections["server"]["ignorelist"]:
            return

        # Ignore chat messages from users who've been ignore-by-ip, no matter whether their username has changed
        # must have the user's IP for this to work.
        if msg.user in self.frame.np.users and type(self.frame.np.users[msg.user].addr) is tuple:
            ip, port = self.frame.np.users[msg.user].addr
            if self.frame.np.ipIgnored(ip):
                return

        self.joinedrooms[msg.room].SayChatRoom(msg, text)

    def PublicRoomMessage(self, msg, text):

        try:
            room = self.joinedrooms['Public ']
        except KeyError:
            return

        room.SayChatRoom(msg, text, public=True)

    def UpdateColours(self):

        self.frame.SetTextBG(self.frame.roomlist.SearchRooms)

        for room in self.joinedrooms.values():
            room.ChangeColours()

    def saveColumns(self):

        for room in list(self.frame.np.config.sections["columns"]["chatrooms"].keys())[:]:
            if room not in self.joinedrooms:
                del self.frame.np.config.sections["columns"]["chatrooms"][room]

        for room in list(self.frame.np.config.sections["columns"]["chatrooms_widths"].keys())[:]:
            if room not in self.joinedrooms:
                del self.frame.np.config.sections["columns"]["chatrooms_widths"][room]

        for room in self.joinedrooms.values():
            room.saveColumns()

    def LeaveRoom(self, msg):

        room = self.joinedrooms[msg.room]

        self.ChatNotebook.remove_page(room.Main)

        room.destroy()

        del self.joinedrooms[msg.room]

        if msg.room[-1:] != ' ':  # meta rooms
            self.frame.RoomSearchCombo_List.remove(self.frame.searchroomslist[msg.room])

    def ConnClose(self):

        self.roomsmodel.clear()

        for room in self.joinedrooms.values():
            room.ConnClose()

        self.autojoin = 1

    def UpdateCompletions(self):

        self.clist = []
        config = self.frame.np.config.sections["words"]

        if config["tab"]:

            config = self.frame.np.config.sections["words"]
            clist = [self.frame.np.config.sections["server"]["login"], "nicotine"]

            if config["roomnames"]:
                clist += self.rooms

            if config["buddies"]:
                clist += [i[0] for i in self.frame.np.config.sections["server"]["userlist"]]

            if config["aliases"]:
                clist += ["/" + k for k in list(self.frame.np.config.aliases.keys())]

            if config["commands"]:
                clist += self.CMDS

            self.clist = clist

        for room in self.joinedrooms.values():
            room.GetCompletionList(clist=list(self.clist))


class ChatRoom:

    def __init__(self, roomsctrl, room, users, meta=False):

        self.roomsctrl = roomsctrl

        self.frame = roomsctrl.frame

        # Build the window
        builder = gtk.Builder()

        builder.set_translation_domain('nicotine')
        builder.add_from_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "chatrooms.ui"))

        self.ChatRoomTab = builder.get_object("ChatRoomTab")

        for i in builder.get_objects():
            try:
                self.__dict__[gtk.Buildable.get_name(i)] = i
            except TypeError:
                pass

        self.ChatRoomTab.remove(self.Main)
        self.ChatRoomTab.destroy()

        builder.connect_signals(self)

        self.Tickers = Tickers()
        self.RoomWall = RoomWall(self.frame, self)

        self.room = room
        self.leaving = 0
        self.meta = meta  # not a real room if set to True
        config = self.frame.np.config.sections

        self.OnShowChatButtons()

        self.clist = []

        # Log Text Search
        TextSearchBar(self.RoomLog, self.LogSearchBar, self.LogSearchEntry)

        # Chat Text Search
        TextSearchBar(self.ChatScroll, self.ChatSearchBar, self.ChatSearchEntry)

        # Spell Check
        if self.frame.gspell and self.frame.np.config.sections["ui"]["spellcheck"]:
            from gi.repository import Gspell
            spell_buffer = Gspell.EntryBuffer.get_from_gtk_entry_buffer(self.ChatEntry.get_buffer())
            spell_buffer.set_spell_checker(Gspell.Checker.new())
            spell_view = Gspell.Entry.get_from_gtk_entry(self.ChatEntry)
            spell_view.set_inline_spell_checking(True)

        self.midwaycompletion = False  # True if the user just used tab completion
        self.completions = {}  # Holds temp. information about tab completoin
        completion = gtk.EntryCompletion()
        self.ChatEntry.set_completion(completion)
        liststore = gtk.ListStore(gobject.TYPE_STRING)
        completion.set_model(liststore)
        completion.set_text_column(0)

        completion.set_match_func(self.frame.EntryCompletionFindMatch, self.ChatEntry)
        completion.connect("match-selected", self.frame.EntryCompletionFoundMatch, self.ChatEntry)

        self.Log.set_active(config["logging"]["chatrooms"])
        if not self.Log.get_active():
            self.Log.set_active((self.room in config["logging"]["rooms"]))

        if room in config["server"]["autojoin"]:
            self.AutoJoin.set_active(True)

        if room not in config["columns"]["chatrooms_widths"]:
            config["columns"]["chatrooms_widths"][room] = [0, 25, 100, 0, 0]

        widths = self.frame.np.config.sections["columns"]["chatrooms_widths"][room]
        self.cols = cols = InitialiseColumns(
            self.UserList,
            [_("Status"), widths[0], "pixbuf"],
            [_("Country"), widths[1], "pixbuf"],
            [_("User"), widths[2], "text", self.UserColumnDraw],
            [_("Speed"), widths[3], "number", self.frame.CellDataFunc],
            [_("Files"), widths[4], "number", self.frame.CellDataFunc]
        )

        cols[0].set_sort_column_id(5)
        cols[1].set_sort_column_id(8)
        cols[2].set_sort_column_id(2)
        cols[3].set_sort_column_id(6)
        cols[4].set_sort_column_id(7)
        cols[0].get_widget().hide()
        cols[1].get_widget().hide()

        if room not in config["columns"]["chatrooms"]:
            config["columns"]["chatrooms"][room] = [1, 1, 1, 1, 1]

        if len(config["columns"]["chatrooms"][room]) != 5:  # Insert new column to old settings.
            config["columns"]["chatrooms"][room].insert(1, 1)

        HideColumns(cols, config["columns"]["chatrooms"][room])

        if config["columns"]["hideflags"]:
            cols[1].set_visible(0)
            config["columns"]["chatrooms"][room][1] = 0

        self.users = {}

        self.usersmodel = gtk.ListStore(
            gobject.TYPE_OBJECT,
            gobject.TYPE_OBJECT,
            gobject.TYPE_STRING,
            gobject.TYPE_STRING,
            gobject.TYPE_STRING,
            gobject.TYPE_INT,
            gobject.TYPE_INT,
            gobject.TYPE_INT,
            gobject.TYPE_STRING
        )

        for username, user in users.items():

            img = self.frame.GetStatusImage(user.status)
            flag = user.country

            if flag:
                flag = "flag_" + flag
                self.frame.flag_users[username] = flag
            else:
                flag = self.frame.GetUserFlag(username)

            hspeed = HumanSpeed(user.avgspeed)
            hfiles = Humanize(user.files)
            iter = self.usersmodel.append(
                [img, self.frame.GetFlagImage(flag), username, hspeed, hfiles, user.status, user.avgspeed, user.files, flag]
            )
            self.users[username] = iter
            self.roomsctrl.GetUserAddress(username)

        self.usersmodel.set_sort_column_id(2, gtk.SortType.ASCENDING)

        self.UpdateColours()

        self.UserList.set_model(self.usersmodel)

        self.popup_menu_privaterooms = PopupMenu(self.frame, False)
        self.popup_menu = popup = PopupMenu(self.frame)

        popup.setup(
            ("USER", "", popup.OnCopyUser),
            ("", None),
            ("#" + _("Send _message"), popup.OnSendMessage),
            ("", None),
            ("#" + _("Show IP a_ddress"), popup.OnShowIPaddress),
            ("#" + _("Get user i_nfo"), popup.OnGetUserInfo),
            ("#" + _("Brow_se files"), popup.OnBrowseUser),
            ("#" + _("Gi_ve privileges"), popup.OnGivePrivileges),
            ("", None),
            ("$" + _("_Add user to list"), popup.OnAddToList),
            ("$" + _("_Ban this user"), popup.OnBanUser),
            ("$" + _("_Ignore this user"), popup.OnIgnoreUser),
            ("$" + _("B_lock this user's IP Address"), popup.OnBlockUser),
            ("$" + _("Ignore this user's IP Address"), popup.OnIgnoreIP),
            ("", None),
            ("#" + _("Sear_ch this user's files"), popup.OnSearchUser),
            (1, _("Private rooms"), self.popup_menu_privaterooms, self.OnPrivateRooms)
        )

        items = self.popup_menu.get_children()

        self.Menu_SendMessage = items[2]
        self.Menu_ShowIPaddress = items[4]
        self.Menu_GetUserInfo = items[5]
        self.Menu_BrowseUser = items[6]
        self.Menu_GivePrivileges = items[7]
        self.Menu_AddToList = items[9]
        self.Menu_BanUser = items[10]
        self.Menu_IgnoreUser = items[11]
        self.Menu_BlockUser = items[12]
        self.Menu_IgnoreIP = items[13]
        self.Menu_SearchUser = items[15]
        self.Menu_PrivateRooms = items[16]

        self.UserList.connect("button_press_event", self.OnPopupMenu)

        self.ChatEntry.grab_focus()

        self.logpopupmenu = PopupMenu(self.frame).setup(
            ("#" + _("Find"), self.OnFindLogWindow),
            ("", None),
            ("#" + _("Copy"), self.OnCopyRoomLog),
            ("#" + _("Copy All"), self.OnCopyAllRoomLog),
            ("", None),
            ("#" + _("Clear log"), self.OnClearRoomLog)
        )

        self.RoomLog.connect("button-press-event", self.OnPopupRoomLogMenu)

        self.chatpopmenu = PopupMenu(self.frame).setup(
            ("#" + _("Find"), self.OnFindChatLog),
            ("", None),
            ("#" + _("Copy"), self.OnCopyChatLog),
            ("#" + _("Copy All"), self.OnCopyAllChatLog),
            ("", None),
            ("#" + _("Clear log"), self.OnClearChatLog)
        )

        self.ChatScroll.connect("button-press-event", self.OnPopupChatRoomMenu)

        self.buildingcompletion = False

        self.GetCompletionList(clist=list(self.roomsctrl.clist))

        if config["logging"]["readroomlogs"]:
            self.ReadRoomLogs()

        self.CountUsers()

    def RoomStatus(self, column, cellrenderer, model, iter, dummy='dummy'):
        # cellrenderer.set_property("weight", colour)
        pass

    def ReadRoomLogs(self):

        config = self.frame.np.config.sections
        log = os.path.join(
            config["logging"]["roomlogsdir"],
            CleanFile(self.room.replace(os.sep, "-")) + ".log"
        )

        try:
            numlines = int(config["logging"]["readroomlines"])
        except Exception:
            numlines = 15

        try:
            with open(log, 'r', encoding='utf-8') as lines:
                # Only show as many log lines as specified in config
                lines = deque(lines, numlines)

                for line in lines:

                    # Try to parse line for username
                    if len(line) > 20 and line[10].isspace() and line[11].isdigit() and line[20] in ("[", "*"):

                        if line[20] == "[" and line[20:].find("] ") != -1:
                            namepos = line[20:].find("] ")
                            user = line[21:20 + namepos].strip()
                            self.getUserTag(user)
                            usertag = self.tag_users[user]
                        else:
                            user = None
                            usertag = None

                        if user == config["server"]["login"]:
                            tag = self.tag_local
                        elif line[20] == "*":
                            tag = self.tag_me
                        elif line[20 + namepos:].upper().find(config["server"]["login"].upper()) > -1:
                            tag = self.tag_hilite
                        else:
                            tag = self.tag_remote
                    else:
                        user = None
                        tag = None
                        usertag = None

                    line = re.sub(r"\\s\\s+", "  ", line)

                    if user != config["server"]["login"]:
                        AppendLine(self.ChatScroll, self.frame.CensorChat(line), tag, username=user, usertag=usertag, timestamp_format="")
                    else:
                        AppendLine(self.ChatScroll, line, tag, username=user, usertag=usertag, timestamp_format="")

                if len(lines) > 0:
                    AppendLine(self.ChatScroll, _("--- old messages above ---"), self.tag_hilite)

        except IOError:
            pass

        GLib.idle_add(ScrollBottom, self.ChatScroll.get_parent())

    def OnFindLogWindow(self, widget):
        self.LogSearchBar.set_search_mode(True)

    def OnFindChatLog(self, widget):
        self.ChatSearchBar.set_search_mode(True)

    def destroy(self):
        self.Main.destroy()

    def OnPrivateRooms(self, widget):

        if self.popup_menu.user is None or self.popup_menu.user == self.frame.np.config.sections["server"]["login"]:
            return False

        user = self.popup_menu.user
        items = []

        popup = self.popup_menu_privaterooms
        popup.clear()
        popup.set_user(self.popup_menu.user)

        for room in self.roomsctrl.PrivateRooms:

            if not (self.roomsctrl.IsPrivateRoomOwned(room) or self.roomsctrl.IsPrivateRoomOperator(room)):
                continue

            if user in self.roomsctrl.PrivateRooms[room]["users"]:
                items.append(("#" + _("Remove from private room %s") % room, popup.OnPrivateRoomRemoveUser, room))
            else:
                items.append(("#" + _("Add to private room %s") % room, popup.OnPrivateRoomAddUser, room))

            if self.roomsctrl.IsPrivateRoomOwned(room):
                if self.popup_menu.user in self.roomsctrl.PrivateRooms[room]["operators"]:
                    items.append(("#" + _("Remove as operator of %s") % room, popup.OnPrivateRoomRemoveOperator, room))
                else:
                    items.append(("#" + _("Add as operator of %s") % room, popup.OnPrivateRoomAddOperator, room))

        popup.setup(*items)

        return True

    def OnPrivateRoomsUser(self, widget, popup=None):

        if popup is None:
            return

        return True

    def OnPopupMenu(self, widget, event):

        d = self.UserList.get_path_at_pos(int(event.x), int(event.y))

        if not d:
            return

        path, column, x, y = d
        user = self.usersmodel.get_value(self.usersmodel.get_iter(path), 2)

        # Double click starts a private message
        if event.button != 3:
            if event.type == Gdk.EventType._2BUTTON_PRESS:
                self.frame.privatechats.SendMessage(user, None, 1)
                self.frame.ChangeMainPage(None, "private")
            return

        self.popup_menu.editing = True
        self.popup_menu.set_user(user)

        me = (self.popup_menu.user is None or self.popup_menu.user == self.frame.np.config.sections["server"]["login"])

        self.Menu_AddToList.set_active(user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
        self.Menu_BanUser.set_active(user in self.frame.np.config.sections["server"]["banlist"])
        self.Menu_IgnoreUser.set_active(user in self.frame.np.config.sections["server"]["ignorelist"])
        self.Menu_BlockUser.set_active(self.frame.UserIpIsBlocked(user))
        self.Menu_BlockUser.set_sensitive(not me)
        self.Menu_IgnoreIP.set_active(self.frame.UserIpIsIgnored(user))
        self.Menu_IgnoreIP.set_sensitive(not me)
        self.Menu_PrivateRooms.set_sensitive(not me)

        self.popup_menu.editing = False
        self.popup_menu.popup(None, None, None, None, event.button, event.time)

    def OnShowRoomWall(self, widget):
        self.RoomWall.show()

    def OnShowChatHelp(self, widget):
        self.frame.OnAboutChatroomCommands(widget)

    def OnShowChatButtons(self, show=True):

        if self.frame.np.config.sections["ui"]["speechenabled"]:
            self.Speech.show()
        else:
            self.Speech.hide()

    def OnHideStatusLog(self, widget):

        act = widget.get_active()
        if act:
            self.RoomLogWindow.hide()
            self.HideStatusLogImage.set_from_icon_name("go-down-symbolic", gtk.IconSize.BUTTON)
        else:
            self.RoomLogWindow.show()
            self.HideStatusLogImage.set_from_icon_name("go-up-symbolic", gtk.IconSize.BUTTON)

    def OnHideUserList(self, widget):

        act = widget.get_active()
        if act:
            self.vbox5.hide()
            self.HideUserListImage.set_from_icon_name("go-previous-symbolic", gtk.IconSize.BUTTON)
        else:
            self.vbox5.show()
            self.HideUserListImage.set_from_icon_name("go-next-symbolic", gtk.IconSize.BUTTON)

    def TickerSet(self, msg):

        self.Tickers.set_ticker([])
        for user in msg.msgs:
            if user in self.frame.np.config.sections["server"]["ignorelist"] or self.frame.UserIpIsIgnored(user):
                # User ignored, ignore Ticker messages
                return

            self.Tickers.add_ticker(user, msg.msgs[user])

    def TickerAdd(self, msg):

        user = msg.user
        if user in self.frame.np.config.sections["server"]["ignorelist"] or self.frame.UserIpIsIgnored(user):
            # User ignored, ignore Ticker messages
            return

        self.Tickers.add_ticker(msg.user, msg.msg)

    def TickerRemove(self, msg):
        self.Tickers.remove_ticker(msg.user)

    def SayChatRoom(self, msg, text, public=False):
        text = re.sub("\\s\\s+", "  ", text)
        login = self.frame.np.config.sections["server"]["login"]
        user = msg.user

        if user == login:
            tag = self.tag_local
        elif text.upper().find(login.upper()) > -1:
            tag = self.tag_hilite
        else:
            tag = self.tag_remote

        if user != login:

            if tag == self.tag_hilite:

                self.roomsctrl.ChatNotebook.request_hilite(self.Main)
                self.frame.ChatRequestIcon(1, self.Main)

                if self.frame.np.config.sections["notifications"]["notification_popup_chatroom_mention"]:
                    self.frame.notifications.NewNotification(
                        text,
                        title=_("%s mentioned you in the %s room") % (user, self.room),
                        soundnamenotify="bell-window-system",
                        soundnamewin="SystemExclamation"
                    )

            else:
                self.roomsctrl.ChatNotebook.request_changed(self.Main)
                self.frame.ChatRequestIcon(0)

            if self.roomsctrl.ChatNotebook.get_current_page() != self.roomsctrl.ChatNotebook.page_num(self.roomsctrl.joinedrooms[self.room].Main) or \
                self.frame.MainNotebook.get_current_page() != self.frame.MainNotebook.page_num(self.frame.chathbox) or \
                    not self.frame.MainWindow.get_property("visible"):

                if tag == self.tag_hilite:

                    if self.room not in self.frame.hilites["rooms"]:
                        self.frame.notifications.Add("rooms", user, self.room, tab=True)

                elif self.frame.np.config.sections["notifications"]["notification_popup_chatroom"]:
                    self.frame.notifications.NewNotification(
                        text,
                        title=_("Message by %s in the %s room") % (user, self.room)
                    )

        if text[:4] == "/me ":

            if public:
                line = "%s | * %s %s" % (msg.room, user, text[4:])
            else:
                line = "* %s %s" % (user, text[4:])

            speech = line[2:]
            tag = self.tag_me
        else:

            if public:
                line = "%s | [%s] %s" % (msg.room, user, text)
            else:
                line = "[%s] %s" % (user, text)

            speech = text

        line = "\n-- ".join(line.split("\n"))
        if self.Log.get_active():
            timestamp_format = self.frame.np.config.sections["logging"]["log_timestamp"]
            write_log(self.frame.np.config.sections["logging"]["roomlogsdir"], self.room, line, timestamp_format)

        self.getUserTag(user)

        timestamp_format = self.frame.np.config.sections["logging"]["rooms_timestamp"]

        if user != login:

            AppendLine(
                self.ChatScroll, self.frame.CensorChat(line), tag,
                username=user, usertag=self.tag_users[user], timestamp_format=timestamp_format
            )

            if self.Speech.get_active():

                self.frame.notifications.new_tts(
                    self.frame.np.config.sections["ui"]["speechrooms"] % {
                        "room": self.room,
                        "user": self.frame.notifications.tts_clean(user),
                        "message": self.frame.notifications.tts_clean(speech)
                    }
                )
        else:
            AppendLine(
                self.ChatScroll, line, tag,
                username=user, usertag=self.tag_users[user], timestamp_format=timestamp_format
            )

    def getUserTag(self, user):

        if user not in self.users:
            color = "useroffline"
        else:
            color = self.getUserStatusColor(self.usersmodel.get_value(self.users[user], 5))

        if user not in self.tag_users:
            self.tag_users[user] = self.makecolour(self.ChatScroll.get_buffer(), color, user)
            return
        else:
            self.changecolour(self.tag_users[user], color)

    def threadAlias(self, alias):

        text = expand_alias(self.frame.np.config.aliases, alias)
        if not text:
            log.add(_('Alias "%s" returned nothing'), alias)
            return

        if text[:2] == "//":
            text = text[1:]

        self.frame.np.queue.put(slskmessages.SayChatroom(self.room, self.frame.AutoReplace(text)))

    def OnEnter(self, widget):

        text = widget.get_text()

        if not text:
            widget.set_text("")
            return

        if is_alias(self.frame.np.config.aliases, text):
            import _thread
            _thread.start_new_thread(self.threadAlias, (text,))
            widget.set_text("")
            return

        s = text.split(" ", 1)  # string
        cmd = s[0]

        if len(s) == 2:
            args = s[1]
        else:
            args = ""

        byteargs = args.encode('utf-8')  # bytes

        if cmd in ("/alias", "/al"):
            AppendLine(self.ChatScroll, self.frame.np.config.AddAlias(args), self.tag_remote, "")
            if self.frame.np.config.sections["words"]["aliases"]:
                self.frame.chatrooms.roomsctrl.UpdateCompletions()
                self.frame.privatechats.UpdateCompletions()

        elif cmd in ("/unalias", "/un"):
            AppendLine(self.ChatScroll, self.frame.np.config.Unalias(args), self.tag_remote, "")
            if self.frame.np.config.sections["words"]["aliases"]:
                self.frame.chatrooms.roomsctrl.UpdateCompletions()
                self.frame.privatechats.UpdateCompletions()

        elif cmd in ["/w", "/whois", "/info"]:
            if byteargs:
                self.frame.LocalUserInfoRequest(byteargs)
                self.frame.OnUserInfo(None)

        elif cmd in ["/b", "/browse"]:
            if byteargs:
                self.frame.BrowseUser(byteargs)
                self.frame.OnUserBrowse(None)

        elif cmd == "/ip":
            if byteargs:
                user = byteargs
                if user not in self.frame.np.ip_requested:
                    self.frame.np.ip_requested.append(user)
                self.frame.np.queue.put(slskmessages.GetPeerAddress(user))

        elif cmd == "/pm":
            if byteargs:
                self.frame.privatechats.SendMessage(byteargs, None, 1)
                self.frame.OnPrivateChat(None)

        elif cmd in ["/m", "/msg"]:
            if byteargs:
                user = byteargs.split(b" ", 1)[0]
                try:
                    msg = args.split(" ", 1)[1]
                except IndexError:
                    msg = None
                self.frame.privatechats.SendMessage(user, msg)

        elif cmd in ["/s", "/search"]:
            if args:
                self.frame.Searches.DoSearch(args, 0)
                self.frame.OnSearch(None)

        elif cmd in ["/us", "/usearch"]:
            s = byteargs.split(" ", 1)
            if len(s) == 2:
                self.frame.Searches.DoSearch(s[1], 3, [s[0]])
                self.frame.OnSearch(None)

        elif cmd in ["/rs", "/rsearch"]:
            if args:
                self.frame.Searches.DoSearch(args, 1)
                self.frame.OnSearch(None)

        elif cmd in ["/bs", "/bsearch"]:
            if args:
                self.frame.Searches.DoSearch(args, 2)
                self.frame.OnSearch(None)

        elif cmd in ["/j", "/join"]:
            if byteargs:
                self.frame.np.queue.put(slskmessages.JoinRoom(byteargs))

        elif cmd in ["/l", "/leave", "/p", "/part"]:
            if byteargs:
                self.frame.np.queue.put(slskmessages.LeaveRoom(byteargs))
            else:
                self.frame.np.queue.put(slskmessages.LeaveRoom(self.room))

        elif cmd in ["/ad", "/add", "/buddy"]:
            if byteargs:
                self.frame.userlist.AddToList(byteargs)

        elif cmd in ["/rem", "/unbuddy"]:
            if byteargs:
                self.frame.userlist.RemoveFromList(byteargs)

        elif cmd == "/ban":
            if byteargs:
                self.frame.BanUser(byteargs)

        elif cmd == "/ignore":
            if byteargs:
                self.frame.IgnoreUser(byteargs)

        elif cmd == "/ignoreip":
            if byteargs:
                self.frame.IgnoreIP(byteargs)

        elif cmd == "/unban":
            if byteargs:
                self.frame.UnbanUser(byteargs)

        elif cmd == "/unignore":
            if byteargs:
                self.frame.UnignoreUser(byteargs)

        elif cmd in ["/clear", "/cl"]:
            self.ChatScroll.get_buffer().set_text("")

        elif cmd in ["/a", "/away"]:
            self.frame.OnAway(None)

        elif cmd in ["/q", "/quit", "/exit"]:
            self.frame.OnExit(None)
            return  # Avoid gsignal warning

        elif cmd == "/now":
            self.NowPlayingThread()

        elif cmd == "/rescan":

            # Rescan public shares if needed
            if not self.frame.np.config.sections["transfers"]["friendsonly"] and self.np.config.sections["transfers"]["shared"]:
                self.frame.OnRescan()

            # Rescan buddy shares if needed
            if self.frame.np.config.sections["transfers"]["enablebuddyshares"]:
                self.frame.OnBuddyRescan()

        elif cmd in ["/tick", "/t"]:
            self.frame.np.queue.put(slskmessages.RoomTickerSet(self.room, args))

        elif cmd in ("/tickers",):
            self.showTickers()

        elif cmd in ('/toggle',):
            if byteargs:
                self.frame.np.pluginhandler.toggle_plugin(byteargs)

        elif cmd[:1] == "/" and self.frame.np.pluginhandler.TriggerPublicCommandEvent(self.room, cmd[1:], args):
            pass

        elif cmd and cmd[:1] == "/" and cmd != "/me" and cmd[:2] != "//":
            log.add(_("Command %s is not recognized"), text)
            return

        else:

            if text[:2] == "//":
                text = text[1:]

            tuple = self.frame.np.pluginhandler.OutgoingPublicChatEvent(self.room, text)
            if tuple is not None:
                (r, text) = tuple
                self.Say(self.frame.AutoReplace(text))
                self.frame.np.pluginhandler.OutgoingPublicChatNotification(self.room, text)

        self.ChatEntry.set_text("")

    def showTickers(self):
        tickers = self.Tickers.get_tickers()
        header = _("All tickers / wall messages for %(room)s:") % {'room': self.room}
        log.add("%s\n%s" % (header, "\n".join(["[%s] %s" % (user, msg) for (user, msg) in tickers])))

    def Say(self, text):
        text = re.sub("\\s\\s+", "  ", text)
        self.frame.np.queue.put(slskmessages.SayChatroom(self.room, text))

    def NowPlayingThread(self):
        if self.frame.now is None:
            self.frame.now = nowplaying.NowPlaying(self.frame)

        self.frame.now.DisplayNowPlaying(None, test=0, callback=self.Say)

    def UserJoinedRoom(self, username, userdata):

        if username in self.users:
            return

        # Add to completion list, and completion drop-down
        if self.frame.np.config.sections["words"]["tab"]:
            if username not in self.clist:
                self.clist.append(username)
                if self.frame.np.config.sections["words"]["dropdown"]:
                    self.ChatEntry.get_completion().get_model().append([username])

        if username not in self.frame.np.config.sections["server"]["ignorelist"] and not self.frame.UserIpIsIgnored(username):
            AppendLine(self.RoomLog, _("%s joined the room") % username, self.tag_log)

        img = self.frame.GetStatusImage(userdata.status)
        flag = userdata.country

        if flag is not None:
            flag = "flag_" + flag
            self.frame.flag_users[username] = flag
        else:
            flag = self.frame.GetUserFlag(username)

        hspeed = HumanSpeed(userdata.avgspeed)
        hfiles = Humanize(userdata.files)

        self.users[username] = self.usersmodel.append(
            [img, self.frame.GetFlagImage(flag), username, hspeed, hfiles, userdata.status, userdata.avgspeed, userdata.files, flag]
        )

        self.getUserTag(username)

        self.CountUsers()

    def UserLeftRoom(self, username):

        if username not in self.users:
            return

        # Remove from completion list, and completion drop-down
        if self.frame.np.config.sections["words"]["tab"]:

            if username in self.clist and username not in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]]:

                self.clist.remove(username)

                if self.frame.np.config.sections["words"]["dropdown"]:
                    liststore = self.ChatEntry.get_completion().get_model()

                    iter = liststore.get_iter_first()
                    while iter is not None:
                        name = liststore.get_value(iter, 0)
                        if name == username:
                            liststore.remove(iter)
                            break
                        iter = liststore.iter_next(iter)

        if username not in self.frame.np.config.sections["server"]["ignorelist"] and not self.frame.UserIpIsIgnored(username):
            AppendLine(self.RoomLog, _("%s left the room") % username, self.tag_log)

        self.usersmodel.remove(self.users[username])
        del self.users[username]

        self.getUserTag(username)
        self.CountUsers()

    def CountUsers(self):

        numusers = len(self.users)
        if numusers > 0:
            self.LabelPeople.show()
            self.LabelPeople.set_text(_("User List (%i)") % numusers)
        else:
            self.LabelPeople.hide()

        if self.room in self.roomsctrl.rooms:
            iter = self.roomsctrl.roomsmodel.get_iter_first()
            while iter:
                if self.roomsctrl.roomsmodel.get_value(iter, 0) == self.room:
                    self.roomsctrl.roomsmodel.set(iter, 1, numusers)
                    break
                iter = self.roomsctrl.roomsmodel.iter_next(iter)
        else:
            self.roomsctrl.roomsmodel.append([self.room, numusers, 0])
            self.roomsctrl.rooms.append(self.room)

    def UserColumnDraw(self, column, cellrenderer, model, iter, dummy="dummy"):

        if self.room in self.roomsctrl.PrivateRooms:
            user = self.usersmodel.get_value(iter, 2)

            if user == self.roomsctrl.PrivateRooms[self.room]["owner"]:
                cellrenderer.set_property("underline", pango.Underline.SINGLE)
                cellrenderer.set_property("weight", pango.Weight.BOLD)
            elif user in (self.roomsctrl.PrivateRooms[self.room]["operators"]):
                cellrenderer.set_property("weight", pango.Weight.BOLD)
                cellrenderer.set_property("underline", pango.Underline.NONE)
            else:
                cellrenderer.set_property("weight", pango.Weight.NORMAL)
                cellrenderer.set_property("underline", pango.Underline.NONE)

        self.frame.CellDataFunc(column, cellrenderer, model, iter)

    def GetUserStats(self, user, avgspeed, files):

        if user not in self.users:
            return

        self.usersmodel.set(self.users[user], 3, HumanSpeed(avgspeed), 4, Humanize(files), 6, avgspeed, 7, files)

    def GetUserStatus(self, user, status):

        if user not in self.users:
            return

        img = self.frame.GetStatusImage(status)
        if img == self.usersmodel.get_value(self.users[user], 0):
            return

        if status == 1:
            action = _("%s has gone away")
        else:
            action = _("%s has returned")

        if user not in self.frame.np.config.sections["server"]["ignorelist"] and not self.frame.UserIpIsIgnored(user):
            AppendLine(self.RoomLog, action % user, self.tag_log)

        if user in self.tag_users:
            color = self.getUserStatusColor(status)
            self.changecolour(self.tag_users[user], color)

        self.usersmodel.set(self.users[user], 0, img, 5, status)

    def SetUserFlag(self, user, flag):

        if user not in self.users:
            return

        self.usersmodel.set(self.users[user], 1, self.frame.GetFlagImage(flag), 8, flag)

    def makecolour(self, buffer, colour, username=None):

        colour = self.frame.np.config.sections["ui"][colour]
        font = self.frame.np.config.sections["ui"]["chatfont"]

        tag = buffer.create_tag(font=font)

        if colour:
            tag.set_property("foreground", colour)

        if username is not None:

            usernamestyle = self.frame.np.config.sections["ui"]["usernamestyle"]

            if usernamestyle == "bold":
                tag.set_property("weight", pango.Weight.BOLD)
            else:
                tag.set_property("weight", pango.Weight.NORMAL)

            if usernamestyle == "italic":
                tag.set_property("style", pango.Style.ITALIC)
            else:
                tag.set_property("style", pango.Style.NORMAL)

            if usernamestyle == "underline":
                tag.set_property("underline", pango.Underline.SINGLE)
            else:
                tag.set_property("underline", pango.Underline.NONE)

            tag.connect("event", self.UserNameEvent, username)

        return tag

    def UserNameEvent(self, tag, widget, event, iter, user):

        """
        Mouse buttons:
        1 = left button
        2 = middle button
        3 = right button
        """
        if event.button.type == Gdk.EventType.BUTTON_PRESS and event.button.button in (1, 2, 3):

            # Chat, Userlists use the normal popup system
            self.popup_menu.editing = True
            self.popup_menu.set_user(user)
            me = (self.popup_menu.user is None or self.popup_menu.user == self.frame.np.config.sections["server"]["login"])

            self.Menu_AddToList.set_active(user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
            self.Menu_BanUser.set_active(user in self.frame.np.config.sections["server"]["banlist"])
            self.Menu_IgnoreUser.set_active(user in self.frame.np.config.sections["server"]["ignorelist"])
            self.Menu_BlockUser.set_active(self.frame.UserIpIsBlocked(user))
            self.Menu_BlockUser.set_sensitive(not me)
            self.Menu_IgnoreIP.set_active(self.frame.UserIpIsIgnored(user))
            self.Menu_IgnoreIP.set_sensitive(not me)
            self.Menu_PrivateRooms.set_sensitive(not me)

            self.popup_menu.editing = False
            self.popup_menu.popup(None, None, None, None, event.button.button, event.button.time)

        return True

    def UpdateColours(self):

        self.frame.ChangeListFont(self.UserList, self.frame.np.config.sections["ui"]["listfont"])

        buffer = self.ChatScroll.get_buffer()

        self.tag_remote = self.makecolour(buffer, "chatremote")
        self.tag_local = self.makecolour(buffer, "chatlocal")
        self.tag_me = self.makecolour(buffer, "chatme")
        self.tag_hilite = self.makecolour(buffer, "chathilite")

        self.tag_users = {}
        for user in self.tag_users:
            self.getUserTag(user)

        logbuffer = self.RoomLog.get_buffer()
        self.tag_log = self.makecolour(logbuffer, "chatremote")

        self.frame.SetTextBG(self.ChatEntry)
        self.frame.SetTextBG(self.RoomWall.RoomWallEntry)

    def getUserStatusColor(self, status):

        if status == 1:
            color = "useraway"
        elif status == 2:
            color = "useronline"
        else:
            color = "useroffline"

        if not self.frame.np.config.sections["ui"]["showaway"] and color == "useraway":
            color = "useronline"

        return color

    def changecolour(self, tag, colour):

        color = self.frame.np.config.sections["ui"][colour]

        if color == "":
            color = None

        tag.set_property("foreground", color)

        font = self.frame.np.config.sections["ui"]["chatfont"]
        tag.set_property("font", font)

        # Hotspots
        if colour in ["useraway", "useronline", "useroffline"]:

            usernamestyle = self.frame.np.config.sections["ui"]["usernamestyle"]

            if usernamestyle == "bold":
                tag.set_property("weight", pango.Weight.BOLD)
            else:
                tag.set_property("weight", pango.Weight.NORMAL)

            if usernamestyle == "italic":
                tag.set_property("style", pango.Style.ITALIC)
            else:
                tag.set_property("style", pango.Style.NORMAL)

            if usernamestyle == "underline":
                tag.set_property("underline", pango.Underline.SINGLE)
            else:
                tag.set_property("underline", pango.Underline.NONE)

    def ChangeColours(self):

        self.changecolour(self.tag_remote, "chatremote")
        self.changecolour(self.tag_local, "chatlocal")
        self.changecolour(self.tag_me, "chatme")
        self.changecolour(self.tag_hilite, "chathilite")
        self.changecolour(self.tag_log, "chatremote")

        for user in self.tag_users:
            self.getUserTag(user)

        self.frame.SetTextBG(self.ChatEntry)
        self.frame.SetTextBG(self.RoomWall.RoomWallEntry)
        self.frame.ChangeListFont(self.UserList, self.frame.np.config.sections["ui"]["listfont"])

    def OnLeave(self, widget=None):

        if self.leaving:
            return

        self.leaving = 1

        config = self.frame.np.config.sections

        if self.room in config["columns"]["chatrooms"]:
            del config["columns"]["chatrooms"][self.room]

        if self.room in config["columns"]["chatrooms_widths"]:
            del config["columns"]["chatrooms_widths"][self.room]

        if not self.meta:
            self.frame.np.queue.put(slskmessages.LeaveRoom(self.room))
        else:
            if self.room == 'Public ':
                self.frame.np.queue.put(slskmessages.LeavePublicRoom())
                self.roomsctrl.LeaveRoom(slskmessages.LeaveRoom(self.room))  # Faking protocol msg
            else:
                log.add_warning(_("Unknown meta chatroom closed"))

        self.frame.np.pluginhandler.LeaveChatroomNotification(self.room)

    def saveColumns(self):

        columns = []
        widths = []
        for column in self.UserList.get_columns():
            columns.append(column.get_visible())
            widths.append(column.get_width())

        self.frame.np.config.sections["columns"]["chatrooms"][self.room] = columns
        self.frame.np.config.sections["columns"]["chatrooms_widths"][self.room] = widths

    def ConnClose(self):

        AppendLine(self.ChatScroll, _("--- disconnected ---"), self.tag_hilite)
        self.usersmodel.clear()
        self.UserList.set_sensitive(False)
        self.users.clear()
        self.CountUsers()

        config = self.frame.np.config.sections
        if not self.AutoJoin.get_active() and self.room in config["columns"]["chatrooms"]:
            del config["columns"]["chatrooms"][self.room]

        if not self.AutoJoin.get_active() and self.room in config["columns"]["chatrooms_widths"]:
            del config["columns"]["chatrooms_widths"][self.room]

        for tag in self.tag_users.values():
            self.changecolour(tag, "useroffline")

        self.Tickers.set_ticker([])

    def Rejoined(self, users):

        # Update user list with an inexpensive sorting function
        self.usersmodel.set_default_sort_func(lambda *args: -1)
        self.usersmodel.set_sort_column_id(-1, gtk.SortType.ASCENDING)

        for (username, user) in users.items():

            if username in self.users:
                self.usersmodel.remove(self.users[username])

            img = self.frame.GetStatusImage(user.status)
            flag = user.country

            if flag is not None:
                flag = "flag_" + flag
                self.frame.flag_users[username] = flag
            else:
                flag = self.frame.GetUserFlag(username)

            hspeed = HumanSpeed(user.avgspeed)
            hfiles = Humanize(user.files)

            myiter = self.usersmodel.append([img, self.frame.GetFlagImage(flag), username, hspeed, hfiles, user.status, user.avgspeed, user.files, flag])

            self.users[username] = myiter
            self.roomsctrl.GetUserAddress(username)

        self.UserList.set_sensitive(True)

        # Reinitialize sorting after loop is complet
        self.usersmodel.set_sort_column_id(2, gtk.SortType.ASCENDING)
        self.usersmodel.set_default_sort_func(lambda *args: -1)

        # Spit this line into chat log
        AppendLine(self.ChatScroll, _("--- reconnected ---"), self.tag_hilite)

        # Update user count
        self.CountUsers()

        # Build completion list
        self.GetCompletionList(clist=self.roomsctrl.clist)

        # Update all username tags in chat log
        for user in self.tag_users:
            self.getUserTag(user)

    def OnAutojoin(self, widget):

        autojoin = self.frame.np.config.sections["server"]["autojoin"]

        if not widget.get_active():
            if self.room in autojoin:
                autojoin.remove(self.room)
        else:
            if self.room not in autojoin:
                autojoin.append(self.room)

        self.frame.np.config.writeConfiguration()

    def GetCompletionList(self, ix=0, text="", clist=[]):

        config = self.frame.np.config.sections["words"]

        completion = self.ChatEntry.get_completion()
        completion.set_popup_single_match(not config["onematch"])
        completion.set_minimum_key_length(config["characters"])

        liststore = completion.get_model()
        liststore.clear()

        self.clist = []

        if not config["tab"]:
            return

        if config["roomusers"]:
            clist += list(self.users.keys())

        # no duplicates
        def _combilower(x):
            try:
                return x.lower()
            except Exception:
                return x

        clist = list(set(clist))
        clist.sort(key=_combilower)

        completion.set_popup_completion(False)

        if config["dropdown"]:
            for word in clist:
                liststore.append([word])

            completion.set_popup_completion(True)

        self.clist = clist

    def OnKeyPress(self, widget, event):

        if event.keyval == Gdk.keyval_from_name("Prior"):

            scrolled = self.ChatScroll.get_parent()
            adj = scrolled.get_vadjustment()
            adj.set_value(adj.value - adj.page_increment)

        elif event.keyval == Gdk.keyval_from_name("Next"):

            scrolled = self.ChatScroll.get_parent()
            adj = scrolled.get_vadjustment()
            max = adj.upper - adj.page_size
            new = adj.value + adj.page_increment

            if new > max:
                new = max

            adj.set_value(new)

        # ISO_Left_Tab normally corresponds with shift+tab
        if event.keyval not in (Gdk.keyval_from_name("Tab"), Gdk.keyval_from_name("ISO_Left_Tab")):
            if event.keyval not in (Gdk.keyval_from_name("Shift_L"), Gdk.keyval_from_name("Shift_R")):
                self.midwaycompletion = False
            return False

        config = self.frame.np.config.sections["words"]
        if not config["tab"]:
            return False

        # "Hello there Miss<tab> how are you doing"
        # "0  3  6  9  12 15      18 21 24 27 30 33
        #   1  4  7  10 13      16 19 22 25 28 31
        #    2  5  8  11 14      17 20 23 26 29 32
        #
        # ix = 16
        # text = Miss
        # preix = 12
        ix = widget.get_position()
        text = widget.get_text()[:ix].split(" ")[-1]
        preix = ix - len(text)

        if not config["cycle"]:
            completion, single = GetCompletion(text, self.clist)
            if completion:
                if single:
                    if ix == len(text) and text[:1] != "/":
                        completion += ": "
                widget.delete_text(preix, ix)
                widget.insert_text(completion, preix)
                widget.set_position(preix + len(completion))
        else:

            if not self.midwaycompletion:
                self.completions['completions'] = GetCompletions(text, self.clist)
                if self.completions['completions']:
                    self.midwaycompletion = True
                    self.completions['currentindex'] = -1
                    currentnick = text
            else:
                currentnick = self.completions['completions'][self.completions['currentindex']]

            if self.midwaycompletion:

                widget.delete_text(ix - len(currentnick), ix)
                direction = 1  # Forward cycle

                if event.keyval == Gdk.keyval_from_name("ISO_Left_Tab"):
                    direction = -1  # Backward cycle

                self.completions['currentindex'] = (self.completions['currentindex'] + direction) % len(self.completions['completions'])

                newnick = self.completions['completions'][self.completions['currentindex']]
                widget.insert_text(newnick, preix)
                widget.set_position(preix + len(newnick))

        widget.stop_emission_by_name("key_press_event")

        return True

    def OnTooltip(self, widget, x, y, keyboard_mode, tooltip):
        return showCountryTooltip(widget, x, y, tooltip, 8)

    def OnLogToggled(self, widget):

        if not widget.get_active():
            if self.room in self.frame.np.config.sections["logging"]["rooms"]:
                self.frame.np.config.sections["logging"]["rooms"].remove(self.room)
        elif widget.get_active():
            if self.room not in self.frame.np.config.sections["logging"]["rooms"]:
                self.frame.np.config.sections["logging"]["rooms"].append(self.room)

    def OnPopupChatRoomMenu(self, widget, event):

        if event.button != 3:
            return False

        widget.stop_emission_by_name("button-press-event")
        self.chatpopmenu.popup(None, None, None, None, event.button, event.time)

        return True

    def OnPopupRoomLogMenu(self, widget, event):

        if event.button != 3:
            return False

        widget.stop_emission_by_name("button-press-event")
        self.logpopupmenu.popup(None, None, None, None, event.button, event.time)

        return True

    def OnCopyAllRoomLog(self, widget):
        start, end = self.RoomLog.get_buffer().get_bounds()
        log = self.RoomLog.get_buffer().get_text(start, end, True)
        self.frame.clip.set_text(log, -1)

    def OnCopyRoomLog(self, widget):

        bound = self.RoomLog.get_buffer().get_selection_bounds()

        if bound is not None and len(bound) == 2:
            start, end = bound
            log = self.RoomLog.get_buffer().get_text(start, end, True)
            self.frame.clip.set_text(log, -1)

    def OnCopyChatLog(self, widget):

        bound = self.ChatScroll.get_buffer().get_selection_bounds()

        if bound is not None and len(bound) == 2:
            start, end = bound
            log = self.ChatScroll.get_buffer().get_text(start, end, True)
            self.frame.clip.set_text(log, -1)

    def OnCopyAllChatLog(self, widget):
        start, end = self.ChatScroll.get_buffer().get_bounds()
        log = self.ChatScroll.get_buffer().get_text(start, end, True)
        self.frame.clip.set_text(log, -1)

    def OnClearChatLog(self, widget):
        self.ChatScroll.get_buffer().set_text("")

    def OnClearRoomLog(self, widget):
        self.RoomLog.get_buffer().set_text("")


class ChatRooms(IconNotebook):

    def __init__(self, frame):

        self.frame = frame

        config = self.frame.np.config.sections

        IconNotebook.__init__(
            self,
            self.frame.images,
            angle=config["ui"]["labelrooms"],
            tabclosers=config["ui"]["tabclosers"],
            show_image=config["notifications"]["notification_tab_icons"],
            reorderable=config["ui"]["tab_reorderable"],
            notebookraw=self.frame.ChatNotebookRaw
        )

        self.roomsctrl = RoomsControl(self)

        self.popup_enable()

        self.set_tab_pos(self.frame.getTabPosition(config["ui"]["tabrooms"]))

    def TabPopup(self, room):

        if room not in self.roomsctrl.joinedrooms:
            return

        popup = PopupMenu(self.frame)
        popup.setup(
            ("#" + _("Leave this room"), self.roomsctrl.joinedrooms[room].OnLeave)
        )
        popup.set_user(room)

        return popup

    def on_tab_click(self, widget, event, child):

        if event.type == Gdk.EventType.BUTTON_PRESS:

            n = self.page_num(child)
            page = self.get_nth_page(n)
            room = [room for room, tab in self.roomsctrl.joinedrooms.items() if tab.Main is page][0]

            if event.button == 2:
                self.roomsctrl.joinedrooms[room].OnLeave(widget)
                return True

            if event.button == 3:
                menu = self.TabPopup(room)
                menu.popup(None, None, None, None, event.button, event.time)
                return True

            return False

        return False

    def ConnClose(self):
        self.roomsctrl.ConnClose()
