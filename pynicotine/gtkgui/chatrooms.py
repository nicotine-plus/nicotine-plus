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
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from pynicotine import slskmessages
from pynicotine.gtkgui.dialogs import entry_dialog
from pynicotine.gtkgui.roomwall import RoomWall
from pynicotine.gtkgui.roomwall import Tickers
from pynicotine.gtkgui.utils import append_line
from pynicotine.gtkgui.utils import hide_columns
from pynicotine.gtkgui.utils import humanize
from pynicotine.gtkgui.utils import human_speed
from pynicotine.gtkgui.utils import IconNotebook
from pynicotine.gtkgui.utils import initialise_columns
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.gtkgui.utils import press_header
from pynicotine.gtkgui.utils import scroll_bottom
from pynicotine.gtkgui.utils import TextSearchBar
from pynicotine.gtkgui.utils import expand_alias
from pynicotine.gtkgui.utils import is_alias
from pynicotine.gtkgui.utils import show_country_tooltip
from pynicotine.gtkgui.utils import set_widget_color
from pynicotine.gtkgui.utils import set_widget_font
from pynicotine.gtkgui.utils import update_widget_visuals
from pynicotine.logfacility import log
from pynicotine.utils import clean_file
from pynicotine.utils import cmp
from pynicotine.utils import write_log


def get_completion(part, list):
    matches = get_completions(part, list)
    if len(matches) == 0:
        return None, 0
    if len(matches) == 1:
        return matches[0], 1
    else:
        return commonprefix([x.lower() for x in matches]), 0


def get_completions(part, list):
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

    def __init__(self, chat_notebook):

        self.frame = chat_notebook.frame
        self.chat_notebook = chat_notebook

        self.joinedrooms = {}
        self.autojoin = 1
        self.rooms = []
        config = self.frame.np.config.sections
        self.private_rooms = config["private_rooms"]["rooms"]

        # Config cleanup
        for room, data in self.private_rooms.items():
            if "owner" not in data:
                self.private_rooms[room]["owner"] = None
            if "operator" in data:
                del self.private_rooms[room]["operator"]

        self.clist = []
        self.roomsmodel = Gtk.ListStore(str, int, int)
        self.frame.roomlist.RoomsList.set_model(self.roomsmodel)

        self.cols = initialise_columns(
            self.frame.roomlist.RoomsList,
            [_("Room"), 180, "text", self.room_status],
            [_("Users"), 0, "number", self.room_status]
        )
        self.cols[0].set_sort_column_id(0)
        self.cols[1].set_sort_column_id(1)

        self.roomsmodel.set_sort_func(1, self.private_rooms_sort, 1)

        for i in range(2):
            parent = self.cols[i].get_widget().get_ancestor(Gtk.Button)
            if parent:
                parent.connect('button_press_event', press_header)

        self.popup_room = None
        self.popup_menu = PopupMenu(self.frame).setup(
            ("#" + _("Join Room"), self.on_popup_join),
            ("#" + _("Leave Room"), self.on_popup_leave),
            ("#" + _("Create Room"), self.on_popup_create_public_room),
            ("", None),
            ("#" + _("Create Private Room"), self.on_popup_create_private_room),
            ("#" + _("Disown Private Room"), self.on_popup_private_room_disown),
            ("#" + _("Cancel Room Membership"), self.on_popup_private_room_dismember),
            ("", None),
            ("#" + _("Join Public Room"), self.on_join_public_room),
            ("", None),
            ("#" + _("Refresh"), self.on_popup_refresh)
        )

        items = self.popup_menu.get_children()
        self.menu_join, self.menu_leave, self.menu_create_room, self.menu_empty1, self.menu_private_room_create, self.menu_private_room_disown, self.menu_private_room_dismember, self.menu_empty2, self.menu_join_public_room, self.menu_empty3, self.menu_refresh = items

        self.frame.roomlist.RoomsList.connect("button_press_event", self.on_list_clicked)
        self.frame.roomlist.RoomsList.set_headers_clickable(True)

        self.chat_notebook.notebook.connect("switch-page", self.on_switch_page)
        self.chat_notebook.notebook.connect("page-reordered", self.on_reordered_page)

        self.frame.roomlist.update_visuals()
        self.update_visuals()

    def is_private_room_owned(self, room):

        if room in self.private_rooms:
            if self.private_rooms[room]["owner"] == self.frame.np.config.sections["server"]["login"]:
                return True

        return False

    def is_private_room_member(self, room):

        if room in self.private_rooms:
            return True

        return False

    def is_private_room_operator(self, room):

        if room in self.private_rooms:
            if self.frame.np.config.sections["server"]["login"] in self.private_rooms[room]["operators"]:
                return True

        return False

    def private_rooms_sort(self, model, iter1, iter2, column):

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

    def room_status(self, column, cellrenderer, model, iterator, dummy='dummy'):

        if self.roomsmodel.get_value(iterator, 2) >= 2:
            cellrenderer.set_property("underline", Pango.Underline.SINGLE)
            cellrenderer.set_property("weight", Pango.Weight.BOLD)

        elif self.roomsmodel.get_value(iterator, 2) >= 1:
            cellrenderer.set_property("weight", Pango.Weight.BOLD)
            cellrenderer.set_property("underline", Pango.Underline.NONE)

        else:
            cellrenderer.set_property("weight", Pango.Weight.NORMAL)
            cellrenderer.set_property("underline", Pango.Underline.NONE)

    def on_reordered_page(self, notebook, page, page_num, force=0):

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
        rto = sorted(room_tab_order.keys())
        new_autojoin = []
        for roomplace in rto:
            new_autojoin.append(room_tab_order[roomplace])

        # Save
        self.frame.np.config.sections["server"]["autojoin"] = new_autojoin

    def on_switch_page(self, notebook, page, page_num, forceupdate=False):

        if self.frame.MainNotebook.get_current_page() != self.frame.MainNotebook.page_num(self.frame.chathbox) and not forceupdate:
            return

        for name, room in self.joinedrooms.items():
            if room.Main == page:
                GLib.idle_add(room.ChatEntry.grab_focus)

                # Remove hilite
                self.frame.notifications.clear("rooms", None, name)

    def clear_notifications(self):

        if self.frame.MainNotebook.get_current_page() != self.frame.MainNotebook.page_num(self.frame.chathbox):
            return

        page = self.chat_notebook.get_nth_page(self.chat_notebook.get_current_page())

        for name, room in self.joinedrooms.items():
            if room.Main == page:
                # Remove hilite
                self.frame.notifications.clear("rooms", None, name)

    def focused(self, page, focused):

        if not focused:
            return

        for name, room in self.users.items():
            if room.Main == page:
                self.frame.notifications.clear("rooms", name)

    def on_list_clicked(self, widget, event):

        if event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:

            d = self.frame.roomlist.RoomsList.get_path_at_pos(int(event.x), int(event.y))
            if d:
                path, column, x, y = d
                room = self.roomsmodel.get_value(self.roomsmodel.get_iter(path), 0)
                if room not in self.joinedrooms:
                    self.frame.np.queue.put(slskmessages.JoinRoom(room))

            return True
        elif event.button == 3:
            return self.on_popup_menu(widget, event)

        return False

    def on_popup_menu(self, widget, event):

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

        self.menu_join.set_sensitive(act[0])
        self.menu_leave.set_sensitive(act[1])

        self.menu_private_room_disown.set_sensitive(self.is_private_room_owned(self.popup_room))  # Disown
        self.menu_private_room_dismember.set_sensitive((prooms_enabled and self.is_private_room_member(self.popup_room)))  # Dismember

        self.popup_menu.popup(None, None, None, None, event.button, event.time)

    def on_popup_join(self, widget):
        self.frame.np.queue.put(slskmessages.JoinRoom(self.popup_room))

    def on_popup_create_public_room(self, widget):

        room = entry_dialog(
            self.frame.MainWindow,
            title=_("Create Public Room"),
            message=_('Enter the name of the public room you wish to create')
        )

        if room:
            self.frame.np.queue.put(slskmessages.JoinRoom(room))

    def on_join_public_room(self, widget):

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

        self.chat_notebook.append_page(room.Main, 'Public ', room.on_leave, angle)

        room.count_users()

        self.frame.np.queue.put(slskmessages.JoinPublicRoom())

    def on_popup_create_private_room(self, widget):

        room = entry_dialog(
            self.frame.MainWindow,
            title=_("Create Private Room"),
            message=_('Enter the name of the private room you wish to create')
        )

        if room:
            self.frame.np.queue.put(slskmessages.JoinRoom(room, 1))

    def on_popup_private_room_disown(self, widget):

        if self.is_private_room_owned(self.popup_room):
            self.frame.np.queue.put(slskmessages.PrivateRoomDisown(self.popup_room))
            del self.private_rooms[self.popup_room]
            self.set_private_rooms()

    def on_popup_private_room_dismember(self, widget):

        if self.is_private_room_member(self.popup_room):
            self.frame.np.queue.put(slskmessages.PrivateRoomDismember(self.popup_room))
            del self.private_rooms[self.popup_room]
            self.set_private_rooms()

    def on_popup_leave(self, widget):
        self.frame.np.queue.put(slskmessages.LeaveRoom(self.popup_room))

    def on_popup_refresh(self, widget):
        self.frame.np.queue.put(slskmessages.RoomList())

    def join_room(self, msg):

        if msg.room in self.joinedrooms:
            self.joinedrooms[msg.room].rejoined(msg.users)
            return

        tab = ChatRoom(self, msg.room, msg.users)

        self.joinedrooms[msg.room] = tab

        if msg.private is not None:
            self.create_private_room(msg.room, msg.owner, msg.operators)

        angle = 0
        try:
            angle = int(self.frame.np.config.sections["ui"]["labelrooms"])
        except Exception as e:
            print(e)

        self.chat_notebook.append_page(tab.Main, msg.room, tab.on_leave, angle)

        self.frame.searchroomslist[msg.room] = self.frame.room_search_combo_model.append([(msg.room)])

        tab.count_users()

    def set_room_list(self, msg):

        if self.autojoin:

            self.autojoin = 0
            if self.joinedrooms:
                room_list = list(self.joinedrooms.keys())
            else:
                room_list = self.frame.np.config.sections["server"]["autojoin"]

            for room in room_list:
                if room == 'Public ':
                    self.on_join_public_room(None)
                else:
                    self.frame.np.queue.put(slskmessages.JoinRoom(room))

        self.roomsmodel.clear()
        self.frame.roomlist.RoomsList.set_model(None)
        self.roomsmodel.set_default_sort_func(lambda *args: -1)
        self.roomsmodel.set_sort_func(1, lambda *args: -1)
        self.roomsmodel.set_sort_column_id(-1, Gtk.SortType.ASCENDING)

        self.rooms = []
        for room, users in msg.rooms:
            self.roomsmodel.append([room, users, 0])
            self.rooms.append(room)

        self.set_private_rooms(msg.ownedprivaterooms, msg.otherprivaterooms)
        self.frame.roomlist.RoomsList.set_model(self.roomsmodel)
        self.roomsmodel.set_sort_func(1, self.private_rooms_sort, 1)
        self.roomsmodel.set_sort_column_id(1, Gtk.SortType.DESCENDING)
        self.roomsmodel.set_default_sort_func(self.private_rooms_sort)

        if self.frame.np.config.sections["words"]["roomnames"]:
            self.frame.chatrooms.roomsctrl.update_completions()
            self.frame.privatechats.update_completions()

    def set_private_rooms(self, ownedrooms=[], otherrooms=[]):

        myusername = self.frame.np.config.sections["server"]["login"]

        for room in ownedrooms:
            try:
                self.private_rooms[room[0]]['joined'] = room[1]
                if self.private_rooms[room[0]]['owner'] != myusername:
                    log.add_warning(_("I remember the room %(room)s being owned by %(previous)s, but the server says its owned by %(new)s."), {
                        'room': room[0],
                        'previous': self.private_rooms[room[0]]['owner'],
                        'new': myusername
                    })
                self.private_rooms[room[0]]['owner'] = myusername
            except KeyError:
                self.private_rooms[room[0]] = {"users": [], "joined": room[1], "operators": [], "owner": myusername}

        for room in otherrooms:
            try:
                self.private_rooms[room[0]]['joined'] = room[1]
                if self.private_rooms[room[0]]['owner'] == myusername:
                    log.add_warning(_("I remember the room %(room)s being owned by %(old)s, but the server says that's not true."), {
                        'room': room[0],
                        'old': self.private_rooms[room[0]]['owner'],
                    })
                    self.private_rooms[room[0]]['owner'] = None
            except KeyError:
                self.private_rooms[room[0]] = {"users": [], "joined": room[1], "operators": [], "owner": None}

        iterator = self.roomsmodel.get_iter_first()
        while iterator is not None:
            room = self.roomsmodel.get_value(iterator, 0)
            lastiter = iterator
            iterator = self.roomsmodel.iter_next(iterator)

            if self.is_private_room_owned(room) or self.is_private_room_member(room):
                self.roomsmodel.remove(lastiter)

        for room in self.private_rooms:

            num = self.private_rooms[room]["joined"]

            if self.is_private_room_owned(room):
                self.roomsmodel.prepend([room, num, 2])

            elif self.is_private_room_member(room):
                self.roomsmodel.prepend([room, num, 1])

    def create_private_room(self, room, owner=None, operators=[]):

        if room in self.private_rooms:
            if operators is not None:
                for operator in operators:
                    if operator not in self.private_rooms[room]["operators"]:
                        self.private_rooms[room]["operators"].append(operator)

            self.private_rooms[room]["owner"] = owner
            return

        self.private_rooms[room] = {"users": [], "joined": 0, "operators": operators, "owned": False, "owner": owner}

    def private_room_users(self, msg):

        rooms = self.private_rooms

        if msg.room not in rooms:
            self.create_private_room(msg.room)
            rooms[msg.room]["users"] = msg.users
            rooms[msg.room]["joined"] = msg.numusers
        else:
            rooms[msg.room]["users"] = msg.users
            rooms[msg.room]["joined"] = msg.numusers

        self.set_private_rooms()

    def private_room_owned(self, msg):

        rooms = self.private_rooms

        if msg.room not in rooms:
            self.create_private_room(msg.room)
            rooms[msg.room]["operators"] = msg.operators
        else:
            rooms[msg.room]["operators"] = msg.operators

        self.set_private_rooms()

    def private_room_add_user(self, msg):

        rooms = self.private_rooms

        if msg.room in rooms:
            if msg.user not in rooms[msg.room]["users"]:
                rooms[msg.room]["users"].append(msg.user)

        self.set_private_rooms()

    def private_room_remove_user(self, msg):

        rooms = self.private_rooms

        if msg.room in rooms:
            if msg.user in rooms[msg.room]["users"]:
                rooms[msg.room]["users"].remove(msg.user)

        self.set_private_rooms()

    def private_room_operator_added(self, msg):

        rooms = self.private_rooms

        if msg.room in rooms:
            if self.frame.np.config.sections["server"]["login"] not in rooms[msg.room]["operators"]:
                rooms[msg.room]["operators"].append(self.frame.np.config.sections["server"]["login"])

        self.set_private_rooms()

    def private_room_operator_removed(self, msg):

        rooms = self.private_rooms

        if msg.room in rooms:
            if self.frame.np.config.sections["server"]["login"] in rooms[msg.room]["operators"]:
                rooms[msg.room]["operators"].remove(self.frame.np.config.sections["server"]["login"])

        self.set_private_rooms()

    def private_room_add_operator(self, msg):

        rooms = self.private_rooms

        if msg.room in rooms:
            if msg.user not in rooms[msg.room]["operators"]:
                rooms[msg.room]["operators"].append(msg.user)

        self.set_private_rooms()

    def private_room_remove_operator(self, msg):

        rooms = self.private_rooms

        if msg.room in rooms:
            if msg.user in rooms[msg.room]["operators"]:
                rooms[msg.room]["operators"].remove(msg.user)

        self.set_private_rooms()

    def private_room_added(self, msg):

        rooms = self.private_rooms
        room = msg.room

        if room not in rooms:
            self.create_private_room(room)
            log.add(_("You have been added to a private room: %(room)s"), {"room": room})

        self.set_private_rooms()

    def private_room_removed(self, msg):

        rooms = self.private_rooms

        if msg.room in rooms:
            del rooms[msg.room]

        self.set_private_rooms()

    def toggle_private_rooms(self, enabled):

        self.frame.np.config.sections["server"]["private_chatrooms"] = enabled

    def private_room_disown(self, msg):
        if msg.room in self.private_rooms:
            if self.private_rooms[msg.room]["owner"] == self.frame.np.config.sections["server"]["login"]:
                self.private_rooms[msg.room]["owner"] = None

    def get_user_stats(self, msg):
        for room in self.joinedrooms.values():
            room.get_user_stats(msg.user, msg.avgspeed, msg.files)

    def get_user_status(self, msg):
        for room in self.joinedrooms.values():
            room.get_user_status(msg.user, msg.status)

    def set_user_flag(self, user, flag):
        for room in self.joinedrooms.values():
            room.set_user_flag(user, flag)

    def get_user_address(self, user):

        if user not in self.frame.np.users or self.frame.np.users[user].addr is None:
            self.frame.np.queue.put(slskmessages.GetPeerAddress(user))

    def user_joined_room(self, msg):

        if msg.room in self.joinedrooms:
            self.joinedrooms[msg.room].user_joined_room(msg.username, msg.userdata)
            self.get_user_address(msg.username)

    def user_left_room(self, msg):
        self.joinedrooms[msg.room].user_left_room(msg.username)

    def ticker_set(self, msg):
        self.joinedrooms[msg.room].ticker_set(msg)

    def ticker_add(self, msg):
        self.joinedrooms[msg.room].ticker_add(msg)

    def ticker_remove(self, msg):
        self.joinedrooms[msg.room].ticker_remove(msg)

    def say_chat_room(self, msg, text):
        if msg.user in self.frame.np.config.sections["server"]["ignorelist"]:
            return

        # Ignore chat messages from users who've been ignore-by-ip, no matter whether their username has changed
        # must have the user's IP for this to work.
        if msg.user in self.frame.np.users and isinstance(self.frame.np.users[msg.user].addr, tuple):
            ip, port = self.frame.np.users[msg.user].addr
            if self.frame.np.ip_ignored(ip):
                return

        self.joinedrooms[msg.room].say_chat_room(msg, text)

    def public_room_message(self, msg, text):

        try:
            room = self.joinedrooms['Public ']
        except KeyError:
            return

        room.say_chat_room(msg, text, public=True)

    def update_visuals(self):

        for room in self.joinedrooms.values():
            room.update_visuals()
            room.update_tags()

    def save_columns(self):

        for room in list(self.frame.np.config.sections["columns"]["chatrooms"].keys())[:]:
            if room not in self.joinedrooms:
                del self.frame.np.config.sections["columns"]["chatrooms"][room]

        for room in list(self.frame.np.config.sections["columns"]["chatrooms_widths"].keys())[:]:
            if room not in self.joinedrooms:
                del self.frame.np.config.sections["columns"]["chatrooms_widths"][room]

        for room in self.joinedrooms.values():
            room.save_columns()

    def leave_room(self, msg):

        room = self.joinedrooms[msg.room]

        self.chat_notebook.remove_page(room.Main)
        room.destroy()
        del self.joinedrooms[msg.room]

        if msg.room[-1:] != ' ':  # meta rooms
            self.frame.room_search_combo_model.remove(self.frame.searchroomslist[msg.room])

    def conn_close(self):

        self.roomsmodel.clear()

        for room in self.joinedrooms.values():
            room.conn_close()

        self.autojoin = 1

    def update_completions(self):

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
            room.get_completion_list(clist=list(self.clist))


class ChatRoom:

    def __init__(self, roomsctrl, room, users, meta=False):

        self.roomsctrl = roomsctrl
        self.frame = roomsctrl.frame

        # Build the window
        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "chatrooms.ui"))

        self.tickers = Tickers()
        self.room_wall = RoomWall(self.frame, self)

        self.room = room
        self.leaving = 0
        self.meta = meta  # not a real room if set to True
        config = self.frame.np.config.sections

        self.on_show_chat_buttons()

        self.clist = []

        # Log Text Search
        TextSearchBar(self.RoomLog, self.LogSearchBar, self.LogSearchEntry)

        # Chat Text Search
        TextSearchBar(self.ChatScroll, self.ChatSearchBar, self.ChatSearchEntry)

        # Spell Check
        if self.frame.spell_checker is None:
            self.frame.init_spell_checker()

        if self.frame.spell_checker and self.frame.np.config.sections["ui"]["spellcheck"]:
            from gi.repository import Gspell
            spell_buffer = Gspell.EntryBuffer.get_from_gtk_entry_buffer(self.ChatEntry.get_buffer())
            spell_buffer.set_spell_checker(self.frame.spell_checker)
            spell_view = Gspell.Entry.get_from_gtk_entry(self.ChatEntry)
            spell_view.set_inline_spell_checking(True)

        self.midwaycompletion = False  # True if the user just used tab completion
        self.completions = {}  # Holds temp. information about tab completoin
        completion = Gtk.EntryCompletion()
        self.ChatEntry.set_completion(completion)
        liststore = Gtk.ListStore(GObject.TYPE_STRING)
        completion.set_model(liststore)
        completion.set_text_column(0)

        completion.set_match_func(self.frame.entry_completion_find_match, self.ChatEntry)
        completion.connect("match-selected", self.frame.entry_completion_found_match, self.ChatEntry)

        self.Log.set_active(config["logging"]["chatrooms"])
        if not self.Log.get_active():
            self.Log.set_active((self.room in config["logging"]["rooms"]))

        if room in config["server"]["autojoin"]:
            self.AutoJoin.set_active(True)

        if room not in config["columns"]["chatrooms_widths"]:
            config["columns"]["chatrooms_widths"][room] = [25, 25, 100, 0, 0]

        widths = self.frame.np.config.sections["columns"]["chatrooms_widths"][room]
        self.cols = cols = initialise_columns(
            self.UserList,
            [_("Status"), widths[0], "pixbuf"],
            [_("Country"), widths[1], "pixbuf"],
            [_("User"), widths[2], "text", self.user_column_draw],
            [_("Speed"), widths[3], "number"],
            [_("Files"), widths[4], "number"]
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

        hide_columns(cols, config["columns"]["chatrooms"][room])

        if config["columns"]["hideflags"]:
            cols[1].set_visible(0)
            config["columns"]["chatrooms"][room][1] = 0

        self.users = {}

        self.usersmodel = Gtk.ListStore(
            GObject.TYPE_OBJECT,
            GObject.TYPE_OBJECT,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_INT,
            GObject.TYPE_INT,
            GObject.TYPE_INT,
            GObject.TYPE_STRING
        )

        for username, user in users.items():

            img = self.frame.get_status_image(user.status)
            flag = user.country

            if flag:
                flag = "flag_" + flag
                self.frame.flag_users[username] = flag
            else:
                flag = self.frame.get_user_flag(username)

            hspeed = human_speed(user.avgspeed)
            hfiles = humanize(user.files)
            iterator = self.usersmodel.append(
                [img, self.frame.get_flag_image(flag), username, hspeed, hfiles, user.status, user.avgspeed, user.files, flag]
            )
            self.users[username] = iterator
            self.roomsctrl.get_user_address(username)

        self.usersmodel.set_sort_column_id(2, Gtk.SortType.ASCENDING)

        self.create_tags()
        self.update_visuals()

        self.UserList.set_model(self.usersmodel)

        self.popup_menu_private_rooms = PopupMenu(self.frame, False)
        self.popup_menu = popup = PopupMenu(self.frame)

        popup.setup(
            ("USER", "", popup.on_copy_user),
            ("", None),
            ("#" + _("Send _message"), popup.on_send_message),
            ("", None),
            ("#" + _("Show IP a_ddress"), popup.on_show_ip_address),
            ("#" + _("Get user i_nfo"), popup.on_get_user_info),
            ("#" + _("Brow_se files"), popup.on_browse_user),
            ("#" + _("Gi_ve privileges"), popup.on_give_privileges),
            ("", None),
            ("$" + _("_Add user to list"), popup.on_add_to_list),
            ("$" + _("_Ban this user"), popup.on_ban_user),
            ("$" + _("_Ignore this user"), popup.on_ignore_user),
            ("$" + _("B_lock this user's IP Address"), popup.on_block_user),
            ("$" + _("Ignore this user's IP Address"), popup.on_ignore_ip),
            ("", None),
            ("#" + _("Sear_ch this user's files"), popup.on_search_user),
            (1, _("Private rooms"), self.popup_menu_private_rooms, popup.on_private_rooms, self.popup_menu_private_rooms)
        )

        items = self.popup_menu.get_children()

        self.menu_send_message = items[2]
        self.menu_show_ip_address = items[4]
        self.menu_get_user_info = items[5]
        self.menu_browse_user = items[6]
        self.menu_give_privileges = items[7]
        self.menu_add_to_list = items[9]
        self.menu_ban_user = items[10]
        self.menu_ignore_user = items[11]
        self.menu_block_user = items[12]
        self.menu_ignore_ip = items[13]
        self.menu_search_user = items[15]
        self.menu_private_rooms = items[16]

        self.UserList.connect("button_press_event", self.on_popup_menu)

        self.ChatEntry.grab_focus()

        self.logpopupmenu = PopupMenu(self.frame).setup(
            ("#" + _("Find"), self.on_find_log_window),
            ("", None),
            ("#" + _("Copy"), self.on_copy_room_log),
            ("#" + _("Copy All"), self.on_copy_all_room_log),
            ("", None),
            ("#" + _("Clear log"), self.on_clear_room_log)
        )

        self.RoomLog.connect("button-press-event", self.on_popup_room_log_menu)

        self.chatpopmenu = PopupMenu(self.frame).setup(
            ("#" + _("Find"), self.on_find_chat_log),
            ("", None),
            ("#" + _("Copy"), self.on_copy_chat_log),
            ("#" + _("Copy All"), self.on_copy_all_chat_log),
            ("", None),
            ("#" + _("Clear log"), self.on_clear_chat_log)
        )

        self.ChatScroll.connect("button-press-event", self.on_popup_chat_room_menu)

        self.buildingcompletion = False

        self.get_completion_list(clist=list(self.roomsctrl.clist))

        if config["logging"]["readroomlogs"]:
            self.read_room_logs()

        self.count_users()

    def room_status(self, column, cellrenderer, model, iterator, dummy='dummy'):
        # cellrenderer.set_property("weight", colour)
        pass

    def read_room_logs(self):

        config = self.frame.np.config.sections
        log = os.path.join(
            config["logging"]["roomlogsdir"],
            clean_file(self.room.replace(os.sep, "-")) + ".log"
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
                            self.get_user_tag(user)
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
                        append_line(self.ChatScroll, self.frame.censor_chat(line), tag, username=user, usertag=usertag, timestamp_format="")
                    else:
                        append_line(self.ChatScroll, line, tag, username=user, usertag=usertag, timestamp_format="")

                if len(lines) > 0:
                    append_line(self.ChatScroll, _("--- old messages above ---"), self.tag_hilite)

        except IOError:
            pass

        GLib.idle_add(scroll_bottom, self.ChatScroll.get_parent())

    def on_find_log_window(self, widget):
        self.LogSearchBar.set_search_mode(True)

    def on_find_chat_log(self, widget):
        self.ChatSearchBar.set_search_mode(True)

    def destroy(self):
        self.Main.destroy()

    def on_popup_menu(self, widget, event):

        d = self.UserList.get_path_at_pos(int(event.x), int(event.y))

        if not d:
            return

        path, column, x, y = d
        user = self.usersmodel.get_value(self.usersmodel.get_iter(path), 2)

        # Double click starts a private message
        if event.button != 3:
            if event.type == Gdk.EventType._2BUTTON_PRESS:
                self.frame.privatechats.send_message(user, show_user=True)
                self.frame.change_main_page("private")
            return

        self.popup_menu.editing = True
        self.popup_menu.set_user(user)

        me = (self.popup_menu.user is None or self.popup_menu.user == self.frame.np.config.sections["server"]["login"])

        self.menu_add_to_list.set_active(user in (i[0] for i in self.frame.np.config.sections["server"]["userlist"]))
        self.menu_ban_user.set_active(user in self.frame.np.config.sections["server"]["banlist"])
        self.menu_ignore_user.set_active(user in self.frame.np.config.sections["server"]["ignorelist"])
        self.menu_block_user.set_active(self.frame.user_ip_is_blocked(user))
        self.menu_block_user.set_sensitive(not me)
        self.menu_ignore_ip.set_active(self.frame.user_ip_is_ignored(user))
        self.menu_ignore_ip.set_sensitive(not me)
        self.menu_private_rooms.set_sensitive(not me)

        self.popup_menu.editing = False
        self.popup_menu.popup(None, None, None, None, event.button, event.time)

    def on_show_room_wall(self, widget):
        self.room_wall.show()

    def on_show_chat_help(self, widget):
        self.frame.on_about_chatroom_commands(widget)

    def on_show_chat_buttons(self, show=True):

        if self.frame.np.config.sections["ui"]["speechenabled"]:
            self.Speech.show()
        else:
            self.Speech.hide()

    def on_hide_status_log(self, widget):

        act = widget.get_active()
        if act:
            self.RoomLogWindow.hide()
            self.HideStatusLogImage.set_from_icon_name("go-down-symbolic", Gtk.IconSize.BUTTON)
        else:
            self.RoomLogWindow.show()
            self.HideStatusLogImage.set_from_icon_name("go-up-symbolic", Gtk.IconSize.BUTTON)

    def on_hide_user_list(self, widget):

        act = widget.get_active()
        if act:
            self.vbox5.hide()
            self.HideUserListImage.set_from_icon_name("go-previous-symbolic", Gtk.IconSize.BUTTON)
        else:
            self.vbox5.show()
            self.HideUserListImage.set_from_icon_name("go-next-symbolic", Gtk.IconSize.BUTTON)

    def ticker_set(self, msg):

        self.tickers.set_ticker([])
        for user in msg.msgs:
            if user in self.frame.np.config.sections["server"]["ignorelist"] or self.frame.user_ip_is_ignored(user):
                # User ignored, ignore Ticker messages
                return

            self.tickers.add_ticker(user, msg.msgs[user])

    def ticker_add(self, msg):

        user = msg.user
        if user in self.frame.np.config.sections["server"]["ignorelist"] or self.frame.user_ip_is_ignored(user):
            # User ignored, ignore Ticker messages
            return

        self.tickers.add_ticker(msg.user, msg.msg)

    def ticker_remove(self, msg):
        self.tickers.remove_ticker(msg.user)

    def say_chat_room(self, msg, text, public=False):
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

                self.roomsctrl.chat_notebook.request_hilite(self.Main)
                self.frame.request_tab_icon(self.frame.ChatTabLabel, status=1)

                if self.frame.np.config.sections["notifications"]["notification_popup_chatroom_mention"]:
                    self.frame.notifications.new_notification(
                        text,
                        title=_("%s mentioned you in the %s room") % (user, self.room),
                        priority=Gio.NotificationPriority.HIGH
                    )

            else:
                self.roomsctrl.chat_notebook.request_changed(self.Main)
                self.frame.request_tab_icon(self.frame.ChatTabLabel, status=0)

            if self.roomsctrl.chat_notebook.get_current_page() != self.roomsctrl.chat_notebook.page_num(self.roomsctrl.joinedrooms[self.room].Main) or \
                self.frame.MainNotebook.get_current_page() != self.frame.MainNotebook.page_num(self.frame.chathbox) or \
                    not self.frame.MainWindow.get_property("visible"):

                if tag == self.tag_hilite:

                    if self.room not in self.frame.hilites["rooms"]:
                        self.frame.notifications.add("rooms", user, self.room, tab=True)

                elif self.frame.np.config.sections["notifications"]["notification_popup_chatroom"]:
                    self.frame.notifications.new_notification(
                        text,
                        title=_("Message by %s in the %s room") % (user, self.room),
                        priority=Gio.NotificationPriority.HIGH
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

        self.get_user_tag(user)

        timestamp_format = self.frame.np.config.sections["logging"]["rooms_timestamp"]

        if user != login:

            append_line(
                self.ChatScroll, self.frame.censor_chat(line), tag,
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
            append_line(
                self.ChatScroll, line, tag,
                username=user, usertag=self.tag_users[user], timestamp_format=timestamp_format
            )

    def get_user_tag(self, user):

        if user not in self.users:
            color = "useroffline"
        else:
            color = self.get_user_status_color(self.usersmodel.get_value(self.users[user], 5))

        if user not in self.tag_users:
            self.tag_users[user] = self.create_tag(self.ChatScroll.get_buffer(), color, user)
        else:
            self.update_tag_visuals(self.tag_users[user], color)

    def thread_alias(self, alias):

        text = expand_alias(self.frame.np.config.aliases, alias)
        if not text:
            log.add(_('Alias "%s" returned nothing'), alias)
            return

        if text[:2] == "//":
            text = text[1:]

        self.frame.np.queue.put(slskmessages.SayChatroom(self.room, self.frame.auto_replace(text)))

    def on_enter(self, widget):

        text = widget.get_text()

        if not text:
            widget.set_text("")
            return

        if is_alias(self.frame.np.config.aliases, text):
            import _thread
            _thread.start_new_thread(self.thread_alias, (text,))
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
            append_line(self.ChatScroll, self.frame.np.config.add_alias(args), self.tag_remote, "")
            if self.frame.np.config.sections["words"]["aliases"]:
                self.frame.chatrooms.roomsctrl.update_completions()
                self.frame.privatechats.update_completions()

        elif cmd in ("/unalias", "/un"):
            append_line(self.ChatScroll, self.frame.np.config.unalias(args), self.tag_remote, "")
            if self.frame.np.config.sections["words"]["aliases"]:
                self.frame.chatrooms.roomsctrl.update_completions()
                self.frame.privatechats.update_completions()

        elif cmd in ["/w", "/whois", "/info"]:
            if byteargs:
                self.frame.local_user_info_request(byteargs)
                self.frame.on_user_info(None)

        elif cmd in ["/b", "/browse"]:
            if byteargs:
                self.frame.browse_user(byteargs)
                self.frame.on_user_browse(None)

        elif cmd == "/ip":
            if byteargs:
                user = byteargs
                self.frame.np.ip_requested.add(user)
                self.frame.np.queue.put(slskmessages.GetPeerAddress(user))

        elif cmd == "/pm":
            if byteargs:
                self.frame.privatechats.send_message(byteargs, show_user=True)
                self.frame.change_main_page("private")

        elif cmd in ["/m", "/msg"]:
            if byteargs:
                user = byteargs.split(b" ", 1)[0]
                try:
                    msg = args.split(" ", 1)[1]
                except IndexError:
                    msg = None
                self.frame.privatechats.send_message(user, msg)

        elif cmd in ["/s", "/search"]:
            if args:
                self.frame.searches.do_search(args, 0)
                self.frame.on_search(None)

        elif cmd in ["/us", "/usearch"]:
            s = byteargs.split(" ", 1)
            if len(s) == 2:
                self.frame.searches.do_search(s[1], 3, [s[0]])
                self.frame.on_search(None)

        elif cmd in ["/rs", "/rsearch"]:
            if args:
                self.frame.searches.do_search(args, 1)
                self.frame.on_search(None)

        elif cmd in ["/bs", "/bsearch"]:
            if args:
                self.frame.searches.do_search(args, 2)
                self.frame.on_search(None)

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
                self.frame.userlist.add_to_list(byteargs)

        elif cmd in ["/rem", "/unbuddy"]:
            if byteargs:
                self.frame.userlist.remove_from_list(byteargs)

        elif cmd == "/ban":
            if byteargs:
                self.frame.ban_user(byteargs)

        elif cmd == "/ignore":
            if byteargs:
                self.frame.ignore_user(byteargs)

        elif cmd == "/ignoreip":
            if byteargs:
                self.frame.ignore_ip(byteargs)

        elif cmd == "/unban":
            if byteargs:
                self.frame.unban_user(byteargs)

        elif cmd == "/unignore":
            if byteargs:
                self.frame.unignore_user(byteargs)

        elif cmd in ["/clear", "/cl"]:
            self.ChatScroll.get_buffer().set_text("")

        elif cmd in ["/a", "/away"]:
            self.frame.on_away(None)

        elif cmd in ["/q", "/quit", "/exit"]:
            self.frame.on_quit(None)
            return  # Avoid gsignal warning

        elif cmd == "/now":
            self.display_now_playing()

        elif cmd == "/rescan":

            # Rescan public shares if needed
            if not self.frame.np.config.sections["transfers"]["friendsonly"] and self.np.config.sections["transfers"]["shared"]:
                self.frame.on_rescan()

            # Rescan buddy shares if needed
            if self.frame.np.config.sections["transfers"]["enablebuddyshares"]:
                self.frame.on_buddy_rescan()

        elif cmd in ["/tick", "/t"]:
            self.frame.np.queue.put(slskmessages.RoomTickerSet(self.room, args))

        elif cmd in ("/tickers",):
            self.show_tickers()

        elif cmd in ('/toggle',):
            if byteargs:
                self.frame.np.pluginhandler.toggle_plugin(byteargs)

        elif cmd[:1] == "/" and self.frame.np.pluginhandler.trigger_public_command_event(self.room, cmd[1:], args):
            pass

        elif cmd and cmd[:1] == "/" and cmd != "/me" and cmd[:2] != "//":
            log.add(_("Command %s is not recognized"), text)
            return

        else:

            if text[:2] == "//":
                text = text[1:]

            event = self.frame.np.pluginhandler.outgoing_public_chat_event(self.room, text)
            if event is not None:
                (r, text) = event
                self.say(self.frame.auto_replace(text))
                self.frame.np.pluginhandler.outgoing_public_chat_notification(self.room, text)

        self.ChatEntry.set_text("")

    def show_tickers(self):
        tickers = self.tickers.get_tickers()
        header = _("All tickers / wall messages for %(room)s:") % {'room': self.room}
        log.add("%s\n%s" % (header, "\n".join(["[%s] %s" % (user, msg) for (user, msg) in tickers])))

    def say(self, text):
        text = re.sub("\\s\\s+", "  ", text)
        self.frame.np.queue.put(slskmessages.SayChatroom(self.room, text))

    def display_now_playing(self):
        self.frame.now_playing.display_now_playing(callback=self.say)

    def user_joined_room(self, username, userdata):

        if username in self.users:
            return

        # Add to completion list, and completion drop-down
        if self.frame.np.config.sections["words"]["tab"]:
            if username not in self.clist:
                self.clist.append(username)
                if self.frame.np.config.sections["words"]["dropdown"]:
                    self.ChatEntry.get_completion().get_model().append([username])

        if username not in self.frame.np.config.sections["server"]["ignorelist"] and not self.frame.user_ip_is_ignored(username):
            append_line(self.RoomLog, _("%s joined the room") % username, self.tag_log)

        img = self.frame.get_status_image(userdata.status)
        flag = userdata.country

        if flag is not None:
            flag = "flag_" + flag
            self.frame.flag_users[username] = flag
        else:
            flag = self.frame.get_user_flag(username)

        hspeed = human_speed(userdata.avgspeed)
        hfiles = humanize(userdata.files)

        self.users[username] = self.usersmodel.append(
            [img, self.frame.get_flag_image(flag), username, hspeed, hfiles, userdata.status, userdata.avgspeed, userdata.files, flag]
        )

        self.get_user_tag(username)

        self.count_users()

    def user_left_room(self, username):

        if username not in self.users:
            return

        # Remove from completion list, and completion drop-down
        if self.frame.np.config.sections["words"]["tab"]:

            if username in self.clist and username not in (i[0] for i in self.frame.np.config.sections["server"]["userlist"]):

                self.clist.remove(username)

                if self.frame.np.config.sections["words"]["dropdown"]:
                    liststore = self.ChatEntry.get_completion().get_model()

                    iterator = liststore.get_iter_first()
                    while iterator is not None:
                        name = liststore.get_value(iterator, 0)
                        if name == username:
                            liststore.remove(iterator)
                            break
                        iterator = liststore.iter_next(iterator)

        if username not in self.frame.np.config.sections["server"]["ignorelist"] and not self.frame.user_ip_is_ignored(username):
            append_line(self.RoomLog, _("%s left the room") % username, self.tag_log)

        self.usersmodel.remove(self.users[username])
        del self.users[username]

        self.get_user_tag(username)
        self.count_users()

    def count_users(self):

        numusers = len(self.users)
        self.LabelPeople.set_markup("<b>%d</b>" % numusers)

        if self.room in self.roomsctrl.rooms:
            iterator = self.roomsctrl.roomsmodel.get_iter_first()
            while iterator:
                if self.roomsctrl.roomsmodel.get_value(iterator, 0) == self.room:
                    self.roomsctrl.roomsmodel.set(iterator, 1, numusers)
                    break
                iterator = self.roomsctrl.roomsmodel.iter_next(iterator)
        else:
            self.roomsctrl.roomsmodel.append([self.room, numusers, 0])
            self.roomsctrl.rooms.append(self.room)

    def user_column_draw(self, column, cellrenderer, model, iterator, dummy="dummy"):

        if self.room in self.roomsctrl.private_rooms:
            user = self.usersmodel.get_value(iterator, 2)

            if user == self.roomsctrl.private_rooms[self.room]["owner"]:
                cellrenderer.set_property("underline", Pango.Underline.SINGLE)
                cellrenderer.set_property("weight", Pango.Weight.BOLD)

            elif user in (self.roomsctrl.private_rooms[self.room]["operators"]):
                cellrenderer.set_property("weight", Pango.Weight.BOLD)
                cellrenderer.set_property("underline", Pango.Underline.NONE)

            else:
                cellrenderer.set_property("weight", Pango.Weight.NORMAL)
                cellrenderer.set_property("underline", Pango.Underline.NONE)

    def get_user_stats(self, user, avgspeed, files):

        if user not in self.users:
            return

        self.usersmodel.set(self.users[user], 3, human_speed(avgspeed), 4, humanize(files), 6, avgspeed, 7, files)

    def get_user_status(self, user, status):

        if user not in self.users:
            return

        img = self.frame.get_status_image(status)
        if img == self.usersmodel.get_value(self.users[user], 0):
            return

        if status == 1:
            action = _("%s has gone away")
        else:
            action = _("%s has returned")

        if user not in self.frame.np.config.sections["server"]["ignorelist"] and not self.frame.user_ip_is_ignored(user):
            append_line(self.RoomLog, action % user, self.tag_log)

        if user in self.tag_users:
            color = self.get_user_status_color(status)
            self.update_tag_visuals(self.tag_users[user], color)

        self.usersmodel.set(self.users[user], 0, img, 5, status)

    def set_user_flag(self, user, flag):

        if user not in self.users:
            return

        self.usersmodel.set(self.users[user], 1, self.frame.get_flag_image(flag), 8, flag)

    def create_tag(self, buffer, color, username=None):

        tag = buffer.create_tag()

        set_widget_color(tag, self.frame.np.config.sections["ui"][color])
        set_widget_font(tag, self.frame.np.config.sections["ui"]["chatfont"])

        if username is not None:

            usernamestyle = self.frame.np.config.sections["ui"]["usernamestyle"]

            if usernamestyle == "bold":
                tag.set_property("weight", Pango.Weight.BOLD)
            else:
                tag.set_property("weight", Pango.Weight.NORMAL)

            if usernamestyle == "italic":
                tag.set_property("style", Pango.Style.ITALIC)
            else:
                tag.set_property("style", Pango.Style.NORMAL)

            if usernamestyle == "underline":
                tag.set_property("underline", Pango.Underline.SINGLE)
            else:
                tag.set_property("underline", Pango.Underline.NONE)

            tag.connect("event", self.user_name_event, username)

        return tag

    def user_name_event(self, tag, widget, event, iterator, user):
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

            self.menu_add_to_list.set_active(user in (i[0] for i in self.frame.np.config.sections["server"]["userlist"]))
            self.menu_ban_user.set_active(user in self.frame.np.config.sections["server"]["banlist"])
            self.menu_ignore_user.set_active(user in self.frame.np.config.sections["server"]["ignorelist"])
            self.menu_block_user.set_active(self.frame.user_ip_is_blocked(user))
            self.menu_block_user.set_sensitive(not me)
            self.menu_ignore_ip.set_active(self.frame.user_ip_is_ignored(user))
            self.menu_ignore_ip.set_sensitive(not me)
            self.menu_private_rooms.set_sensitive(not me)

            self.popup_menu.editing = False
            self.popup_menu.popup(None, None, None, None, event.button.button, event.button.time)

        return True

    def update_visuals(self):

        for widget in self.__dict__.values():
            update_widget_visuals(widget, update_text_tags=False)

        self.room_wall.update_visuals()

    def create_tags(self):

        buffer = self.ChatScroll.get_buffer()

        self.tag_remote = self.create_tag(buffer, "chatremote")
        self.tag_local = self.create_tag(buffer, "chatlocal")
        self.tag_me = self.create_tag(buffer, "chatme")
        self.tag_hilite = self.create_tag(buffer, "chathilite")

        self.tag_users = {}
        for user in self.tag_users:
            self.get_user_tag(user)

        logbuffer = self.RoomLog.get_buffer()
        self.tag_log = self.create_tag(logbuffer, "chatremote")

    def get_user_status_color(self, status):

        if status == 1:
            color = "useraway"
        elif status == 2:
            color = "useronline"
        else:
            color = "useroffline"

        if not self.frame.np.config.sections["ui"]["showaway"] and color == "useraway":
            color = "useronline"

        return color

    def update_tag_visuals(self, tag, color):

        set_widget_color(tag, self.frame.np.config.sections["ui"][color])
        set_widget_font(tag, self.frame.np.config.sections["ui"]["chatfont"])

        # Hotspots
        if color in ("useraway", "useronline", "useroffline"):

            usernamestyle = self.frame.np.config.sections["ui"]["usernamestyle"]

            if usernamestyle == "bold":
                tag.set_property("weight", Pango.Weight.BOLD)
            else:
                tag.set_property("weight", Pango.Weight.NORMAL)

            if usernamestyle == "italic":
                tag.set_property("style", Pango.Style.ITALIC)
            else:
                tag.set_property("style", Pango.Style.NORMAL)

            if usernamestyle == "underline":
                tag.set_property("underline", Pango.Underline.SINGLE)
            else:
                tag.set_property("underline", Pango.Underline.NONE)

    def update_tags(self):

        self.update_tag_visuals(self.tag_remote, "chatremote")
        self.update_tag_visuals(self.tag_local, "chatlocal")
        self.update_tag_visuals(self.tag_me, "chatme")
        self.update_tag_visuals(self.tag_hilite, "chathilite")
        self.update_tag_visuals(self.tag_log, "chatremote")

        for user in self.tag_users:
            self.get_user_tag(user)

    def on_leave(self, widget=None):

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
                self.roomsctrl.leave_room(slskmessages.LeaveRoom(self.room))  # Faking protocol msg
            else:
                log.add_warning(_("Unknown meta chatroom closed"))

        self.frame.np.pluginhandler.leave_chatroom_notification(self.room)

    def save_columns(self):

        columns = []
        widths = []
        for column in self.UserList.get_columns():
            columns.append(column.get_visible())
            widths.append(column.get_width())

        self.frame.np.config.sections["columns"]["chatrooms"][self.room] = columns
        self.frame.np.config.sections["columns"]["chatrooms_widths"][self.room] = widths

    def conn_close(self):

        append_line(self.ChatScroll, _("--- disconnected ---"), self.tag_hilite)
        self.usersmodel.clear()
        self.UserList.set_sensitive(False)
        self.users.clear()
        self.count_users()

        config = self.frame.np.config.sections
        if not self.AutoJoin.get_active() and self.room in config["columns"]["chatrooms"]:
            del config["columns"]["chatrooms"][self.room]

        if not self.AutoJoin.get_active() and self.room in config["columns"]["chatrooms_widths"]:
            del config["columns"]["chatrooms_widths"][self.room]

        for tag in self.tag_users.values():
            self.update_tag_visuals(tag, "useroffline")

        self.tickers.set_ticker([])

    def rejoined(self, users):

        # Update user list with an inexpensive sorting function
        self.usersmodel.set_default_sort_func(lambda *args: -1)
        self.usersmodel.set_sort_column_id(-1, Gtk.SortType.ASCENDING)

        for (username, user) in users.items():

            if username in self.users:
                self.usersmodel.remove(self.users[username])

            img = self.frame.get_status_image(user.status)
            flag = user.country

            if flag is not None:
                flag = "flag_" + flag
                self.frame.flag_users[username] = flag
            else:
                flag = self.frame.get_user_flag(username)

            hspeed = human_speed(user.avgspeed)
            hfiles = humanize(user.files)

            myiter = self.usersmodel.append([img, self.frame.get_flag_image(flag), username, hspeed, hfiles, user.status, user.avgspeed, user.files, flag])

            self.users[username] = myiter
            self.roomsctrl.get_user_address(username)

        self.UserList.set_sensitive(True)

        # Reinitialize sorting after loop is complet
        self.usersmodel.set_sort_column_id(2, Gtk.SortType.ASCENDING)
        self.usersmodel.set_default_sort_func(lambda *args: -1)

        # Spit this line into chat log
        append_line(self.ChatScroll, _("--- reconnected ---"), self.tag_hilite)

        # Update user count
        self.count_users()

        # Build completion list
        self.get_completion_list(clist=self.roomsctrl.clist)

        # Update all username tags in chat log
        for user in self.tag_users:
            self.get_user_tag(user)

    def on_autojoin(self, widget):

        autojoin = self.frame.np.config.sections["server"]["autojoin"]

        if not widget.get_active():
            if self.room in autojoin:
                autojoin.remove(self.room)
        else:
            if self.room not in autojoin:
                autojoin.append(self.room)

        self.frame.np.config.write_configuration()

    def get_completion_list(self, ix=0, text="", clist=None):

        config = self.frame.np.config.sections["words"]

        completion = self.ChatEntry.get_completion()
        completion.set_popup_single_match(not config["onematch"])
        completion.set_minimum_key_length(config["characters"])

        liststore = completion.get_model()
        liststore.clear()

        if clist is None:
            clist = []

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

    def on_key_press(self, widget, event):

        if event.keyval == Gdk.keyval_from_name("Prior"):

            scrolled = self.ChatScroll.get_parent()
            adj = scrolled.get_vadjustment()
            adj.set_value(adj.value - adj.page_increment)

        elif event.keyval == Gdk.keyval_from_name("Next"):

            scrolled = self.ChatScroll.get_parent()
            adj = scrolled.get_vadjustment()
            maximum = adj.upper - adj.page_size
            new = adj.value + adj.page_increment

            if new > maximum:
                new = maximum

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
            completion, single = get_completion(text, self.clist)
            if completion:
                if single:
                    if ix == len(text) and text[:1] != "/":
                        completion += ": "
                widget.delete_text(preix, ix)
                widget.insert_text(completion, preix)
                widget.set_position(preix + len(completion))
        else:

            if not self.midwaycompletion:
                self.completions['completions'] = get_completions(text, self.clist)
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

    def on_tooltip(self, widget, x, y, keyboard_mode, tooltip):
        return show_country_tooltip(widget, x, y, tooltip, 8)

    def on_log_toggled(self, widget):

        if not widget.get_active():
            if self.room in self.frame.np.config.sections["logging"]["rooms"]:
                self.frame.np.config.sections["logging"]["rooms"].remove(self.room)

        elif widget.get_active():
            if self.room not in self.frame.np.config.sections["logging"]["rooms"]:
                self.frame.np.config.sections["logging"]["rooms"].append(self.room)

    def on_popup_chat_room_menu(self, widget, event):

        if event.button != 3:
            return False

        widget.stop_emission_by_name("button-press-event")
        self.chatpopmenu.popup(None, None, None, None, event.button, event.time)

        return True

    def on_popup_room_log_menu(self, widget, event):

        if event.button != 3:
            return False

        widget.stop_emission_by_name("button-press-event")
        self.logpopupmenu.popup(None, None, None, None, event.button, event.time)

        return True

    def on_copy_all_room_log(self, widget):

        start, end = self.RoomLog.get_buffer().get_bounds()
        log = self.RoomLog.get_buffer().get_text(start, end, True)
        self.frame.clip.set_text(log, -1)

    def on_copy_room_log(self, widget):

        bound = self.RoomLog.get_buffer().get_selection_bounds()

        if bound is not None and len(bound) == 2:
            start, end = bound
            log = self.RoomLog.get_buffer().get_text(start, end, True)
            self.frame.clip.set_text(log, -1)

    def on_copy_chat_log(self, widget):

        bound = self.ChatScroll.get_buffer().get_selection_bounds()

        if bound is not None and len(bound) == 2:
            start, end = bound
            log = self.ChatScroll.get_buffer().get_text(start, end, True)
            self.frame.clip.set_text(log, -1)

    def on_copy_all_chat_log(self, widget):

        start, end = self.ChatScroll.get_buffer().get_bounds()
        log = self.ChatScroll.get_buffer().get_text(start, end, True)
        self.frame.clip.set_text(log, -1)

    def on_clear_chat_log(self, widget):
        self.ChatScroll.get_buffer().set_text("")

    def on_clear_room_log(self, widget):
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
            show_hilite_image=config["notifications"]["notification_tab_icons"],
            reorderable=config["ui"]["tab_reorderable"],
            notebookraw=self.frame.ChatNotebookRaw
        )

        self.roomsctrl = RoomsControl(self)

        self.popup_enable()

        self.set_tab_pos(self.frame.get_tab_position(config["ui"]["tabrooms"]))

    def tab_popup(self, room):

        if room not in self.roomsctrl.joinedrooms:
            return

        popup = PopupMenu(self.frame)
        popup.setup(
            ("#" + _("Leave this room"), self.roomsctrl.joinedrooms[room].on_leave)
        )
        popup.set_user(room)

        return popup

    def on_tab_click(self, widget, event, child):

        if event.type == Gdk.EventType.BUTTON_PRESS:

            n = self.page_num(child)
            page = self.get_nth_page(n)
            room = next(room for room, tab in self.roomsctrl.joinedrooms.items() if tab.Main is page)

            if event.button == 2:
                self.roomsctrl.joinedrooms[room].on_leave(widget)
                return True

            if event.button == 3:
                menu = self.tab_popup(room)
                menu.popup(None, None, None, None, event.button, event.time)
                return True

            return False

        return False

    def conn_close(self):
        self.roomsctrl.conn_close()
