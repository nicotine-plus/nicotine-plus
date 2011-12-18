# -*- coding: utf-8 -*-
# Copyright (C) 2007 daelstorm. All rights reserved.
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
#
# Original copyright below
# Copyright (c) 2003-2004 Hyriand. All rights reserved.

# Python core
from os.path import commonprefix
import os, re, time, sys

# Python modules
import gtk
import gobject
import locale
import pango

# Application specific
from pynicotine.logfacility import log
from pynicotine import slskmessages
from pynicotine import pluginsystem
from pynicotine.slskmessages import ToBeEncoded
from utils import InitialiseColumns, AppendLine, PopupMenu, FastListModel, string_sort_func, WriteLog, int_sort_func, Humanize, HumanSpeed, expand_alias, is_alias, EncodingsMenu, SaveEncoding, PressHeader, fixpath, IconNotebook, showCountryTooltip
from pynicotine.utils import _, findBestEncoding
from ticker import Ticker
from entrydialog import OptionDialog, input_box

ver = sys.version_info 

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
	CMDS = set(["/alias ", "/unalias ", "/whois ", "/browse ", "/ip ", "/pm ", "/msg ", "/search ", "/usearch ", "/rsearch ",
		"/bsearch ", "/join ", "/leave ", "/add ", "/buddy ", "/rem ", "/unbuddy ", "/ban ", "/ignore ", "/ignoreip ", "/unban ", "/unignore ",
		"/clear ", "/part ", "/quit ", "/exit ", "/rescan ", "/tick ", "/nsa ", "/info ", "/detach ", "/attach ", "/reload"])
	
	def __init__(self, frame, ChatNotebook):
		self.frame = frame
		self.joinedrooms = {}
		self.autojoin = 1
		self.rooms = []
		config = self.frame.np.config.sections
		self.PrivateRooms =  config["private_rooms"]["rooms"]
		# Config cleanup
		for room,data in self.PrivateRooms.items():
			if "owner" not in data:
				self.PrivateRooms[room]["owner"] = None
			if "operator" in data:
				del self.PrivateRooms[room]["operator"]
		#self.PrivateRoomsMembership = config["private_rooms"]["membership"]
		
		self.clist = []
		self.roomsmodel = gtk.ListStore(str, int, int)
		frame.roomlist.RoomsList.set_model(self.roomsmodel)
		
		self.cols = InitialiseColumns(frame.roomlist.RoomsList,
			[_("Room"), 150, "text", self.RoomStatus],
			[_("Users"), -1, "number", self.RoomStatus],
		)
		self.cols[0].set_sort_column_id(0)
		self.cols[1].set_sort_column_id(1)
		self.roomsmodel.set_sort_func(1, self.PrivateRoomsSort, 1)
		#self.roomsmodel.set_sort_column_id(1, gtk.SORT_DESCENDING)
		#self.cols[1].set_sort_indicator(True)
		
		for i in range (2):
			parent = self.cols[i].get_widget().get_ancestor(gtk.Button)
			if parent:
				parent.connect('button_press_event', PressHeader)

		self.popup_room = None
		self.popup_menu = PopupMenu().setup(
			("#" + _("Join room"), self.OnPopupJoin, gtk.STOCK_JUMP_TO ),
			("#" + _("Leave room"), self.OnPopupLeave, gtk.STOCK_CLOSE),
			( "", None ),
			("#" + _("Enable Private Rooms"), self.OnEnablePrivateRooms, gtk.STOCK_OK),
			("#" + _("Disable Private Rooms"), self.OnDisablePrivateRooms, gtk.STOCK_CANCEL),
			( "", None ),
			("#" + _("Create Private Room"), self.OnPopupCreatePrivateRoom, gtk.STOCK_NEW),
			("#" + _("Disown Private Room"), self.OnPopupPrivateRoomDisown, gtk.STOCK_CLOSE),
			("#" + _("Cancel room membership"), self.OnPopupPrivateRoomDismember, gtk.STOCK_CANCEL),
			( "", None ),
			("#" + _("Join Public Room"), self.OnJoinPublicRoom, gtk.STOCK_DIALOG_WARNING),
			( "", None ),
			("#" + _("Refresh"), self.OnPopupRefresh, gtk.STOCK_REFRESH ),
		)
		
		items = self.popup_menu.get_children()
		self.Menu_Join, self.Menu_Leave, self.Menu_Empty1, self.Menu_PrivateRoom_Enable, self.Menu_PrivateRoom_Disable, self.Menu_Empty2, self.Menu_PrivateRoom_Create, self.Menu_PrivateRoom_Disown, self.Menu_PrivateRoom_Dismember, self.Menu_Empty3, self.Menu_JoinPublicRoom, self.Menu_Empty4, self.Menu_Refresh = items
		self.Menu_PrivateRoom_Enable.set_sensitive(False)
		self.Menu_PrivateRoom_Disable.set_sensitive(False)
		self.Menu_PrivateRoom_Create.set_sensitive(False)
		frame.roomlist.RoomsList.connect("button_press_event", self.OnListClicked)
		frame.roomlist.RoomsList.set_headers_clickable(True)

		frame.roomlist.HideRoomList.connect("clicked", self.OnShowRoomList)

		ChatNotebook.connect("switch-page", self.OnSwitchPage)
		try:
			ChatNotebook.connect("page-reordered", self.OnReorderedPage)
		except:
			# No PyGTK 2.10! Gosh, you really need to get with the times!
			pass
		self.frame.SetTextBG(self.frame.roomlist.RoomsList)
		self.frame.SetTextBG(self.frame.roomlist.CreateRoomEntry)
		self.frame.SetTextBG(self.frame.roomlist.SearchRooms)
		
	def IsPrivateRoomOwned(self, room):
		if room in self.PrivateRooms:
			#print self.PrivateRooms[room]
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
		except:
			private1 = 0
		try:
			private2 = model.get_value(iter2, 2) * 10000
			private2 += model.get_value(iter2, 1)
		except:
			private2 = 0
		return cmp(private1, private2)
		#return cmp(val1+private1, val2+private2)


	def RoomStatus(self, column, cellrenderer, model, iter):

		if self.roomsmodel.get_value(iter, 2) >= 2:
			cellrenderer.set_property("underline", pango.UNDERLINE_SINGLE)
			cellrenderer.set_property("weight", pango.WEIGHT_BOLD)
		elif self.roomsmodel.get_value(iter, 2) >= 1:
			cellrenderer.set_property("weight", pango.WEIGHT_BOLD)
			cellrenderer.set_property("underline", pango.UNDERLINE_NONE)
		else:
			cellrenderer.set_property("weight", pango.WEIGHT_NORMAL)
			cellrenderer.set_property("underline", pango.UNDERLINE_NONE)
		self.frame.CellDataFunc(column, cellrenderer, model, iter)
		
	def OnReorderedPage(self, notebook, page, page_num, force=0):
		room_tab_order = {}
		# Find position of opened autojoined rooms
		for name, room in self.joinedrooms.items():
			if name not in self.frame.np.config.sections["server"]["autojoin"]:
				continue
			room_tab_order [ notebook.page_num(room.Main) ] = name
		pos = 1000
		# Add closed autojoined rooms as well
		for name in self.frame.np.config.sections["server"]["autojoin"]:
			if name not in self.joinedrooms:
				room_tab_order [ pos ] = name
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
		if self.frame.MainNotebook.get_current_page() != self.frame.MainNotebook.page_num(self.frame.hpaned1) and not force:
			return
		page = notebook.get_nth_page(page_num)
		for name, room in self.joinedrooms.items():
			if room.Main == page:
				gobject.idle_add(room.ChatEntry.grab_focus)
				# Remove hilite
				self.frame.Notifications.Clear("rooms", None, name)
					
	def ClearNotifications(self):
		if self.frame.MainNotebook.get_current_page() != self.frame.MainNotebook.page_num(self.frame.hpaned1):
			return
		page = self.frame.ChatNotebook.get_nth_page( self.frame.ChatNotebook.get_current_page())
		for name, room in self.joinedrooms.items():
			if room.Main == page:
				# Remove hilite
				self.frame.Notifications.Clear("rooms", None, name)
				
	def Focused(self, page, focused):
		if not focused:
			return
		for name, room in self.users.items():
			if room.Main == page:
				self.frame.Notifications.Clear("rooms", name)
			
	def OnShowRoomList(self, widget):

		self.frame.show_room_list1.set_active(1)
		
	def OnListClicked(self, widget, event):
		if event.button == 1 and event.type == gtk.gdk._2BUTTON_PRESS:
			d = self.frame.roomlist.RoomsList.get_path_at_pos(int(event.x), int(event.y))
			if d:
				path, column, x, y = d
				room = self.roomsmodel.get_value(self.roomsmodel.get_iter(path), 0)
				if not room in self.joinedrooms:
					self.frame.np.queue.put(slskmessages.JoinRoom(room))
			return True
		elif event.button == 3:
			return self.OnPopupMenu(widget, event)
		return False
		
	def OnPopupMenu(self, widget, event):
		if event.button != 3 or self.roomsmodel is None:
			return
		items = self.popup_menu.get_children()
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
		#prooms_enabled = bool(self.frame.np.config.sections["private_rooms"]["enabled"])
		prooms_enabled = True
		self.Menu_Join.set_sensitive(act[0])
		self.Menu_Leave.set_sensitive(act[1])
		#self.Menu_PrivateRoom_Create.set_sensitive(prooms_enabled) # Create private room
		self.Menu_PrivateRoom_Disown.set_sensitive(self.IsPrivateRoomOwned( self.popup_room)) # Disown
		self.Menu_PrivateRoom_Dismember.set_sensitive((prooms_enabled and self.IsPrivateRoomMember(self.popup_room) )) # Dismember
		self.popup_menu.popup(None, None, None, event.button, event.time)
	
	def OnPopupJoin(self, widget):
		self.frame.np.queue.put(slskmessages.JoinRoom(self.popup_room))
		
	def OnEnablePrivateRooms(self, widget):
		self.frame.np.queue.put(slskmessages.PrivateRoomToggle(True))
	def OnJoinPublicRoom(self, widget):
		# Everything but queue.put shouldn't be here, but the server doesn't send a confirmation when joining
		# public room. It would be clearer if we faked such a message ourself somewhere in the core
		if 'Public ' in self.joinedrooms:
			return
		room = ChatRoom(self, 'Public ', {}, meta = True)
		self.joinedrooms['Public '] = room
		angle = 0
		try:
			angle = int(self.frame.np.config.sections["ui"]["labelrooms"])
		except Exception, e:
			print e
			pass
		self.frame.ChatNotebook.append_page(room.Main, 'Public ', room.OnLeave, angle)
		room.CountUsers()
		self.frame.np.queue.put(slskmessages.JoinPublicRoom())
	def OnDisablePrivateRooms(self, widget):
		self.frame.np.queue.put(slskmessages.PrivateRoomToggle(False))
		
	def OnPopupCreatePrivateRoom(self, widget):
		room = input_box(self.frame, title=_('Nicotine+:')+" "+_("Create Private Room"),
		message=_('Enter the name of the private room you wish to create'),
		default_text='')
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
		except Exception, e:
			print e
			pass
		self.frame.ChatNotebook.append_page(tab.Main, msg.room, tab.OnLeave, angle)
		
		self.frame.searchroomslist[msg.room] = self.frame.RoomSearchCombo_List.append([msg.room])
		tab.CountUsers()
		

	def SetRoomList(self, msg):
		
		if self.autojoin:
			self.autojoin = 0
			if self.joinedrooms:
				list = self.joinedrooms.keys()
			else:
				list = self.frame.np.config.sections["server"]["autojoin"]

			for room in list:
				if room[-1:] != ' ':
					self.frame.np.queue.put(slskmessages.JoinRoom(room))
		self.roomsmodel.clear()
		self.frame.roomlist.RoomsList.set_model(None)
		self.roomsmodel.set_default_sort_func(lambda *args: -1)
		self.roomsmodel.set_sort_func(1, lambda *args: -1)
		self.roomsmodel.set_sort_column_id(-1, gtk.SORT_ASCENDING)

		self.rooms = []
		for room, users in msg.rooms:
			self.roomsmodel.append([room, users, 0])
			self.rooms.append(room)

		self.SetPrivateRooms(msg.ownedprivaterooms, msg.otherprivaterooms)
		self.frame.roomlist.RoomsList.set_model(self.roomsmodel)
		self.roomsmodel.set_sort_func(1, self.PrivateRoomsSort, 1)
		self.roomsmodel.set_sort_column_id(1, gtk.SORT_DESCENDING)
		self.roomsmodel.set_default_sort_func(None)
		#self.cols[1].set_sort_indicator(True)

		if self.frame.np.config.sections["words"]["roomnames"]:
			self.frame.chatrooms.roomsctrl.UpdateCompletions()
			self.frame.privatechats.UpdateCompletions()
			
	def SetPrivateRooms(self, ownedrooms=[], otherrooms=[]):
		myusername = self.frame.np.config.sections["server"]["login"]
		for room in ownedrooms:
			try:
				self.PrivateRooms[room[0]]['joined'] = room[1]
				if self.PrivateRooms[room[0]]['owner'] != myusername:
					log.addwarning(_("I remember the room %(room)s being owned by %(previous)s, but the server says its owned by %(new)s.") % {
							'room': room[0],
							'previous': self.PrivateRooms[room[0]]['owner'],
							'new': myusername
						})
				self.PrivateRooms[room[0]]['owner'] = myusername
			except KeyError:
				self.PrivateRooms[room[0]] = {"users": [], "joined": room[1], "operators": [],  "owner": myusername}
		for room in otherrooms:
			try:
				self.PrivateRooms[room[0]]['joined'] = room[1]
				if self.PrivateRooms[room[0]]['owner'] == myusername:
					log.addwarning(_("I remember the room %(room)s being owned by %(old)s, but the server says that's not true.") % {
							'room': room[0],
							'old': self.PrivateRooms[room[0]]['owner'],
						})
					self.PrivateRooms[room[0]]['owner'] = None
			except KeyError:
				self.PrivateRooms[room[0]] = {"users": [], "joined": room[1], "operators": [],  "owner": None}
		iter = self.roomsmodel.get_iter_root()
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
		self.PrivateRooms[room] = {"users": [], "joined": 0, "operators": operators, "owned":False, "owner":owner}
		
	def PrivateRoomUsers(self, msg):
		rooms = self.PrivateRooms
		if msg.room not in rooms:
			self.CreatePrivateRoom(msg.room)
			rooms[msg.room]["users"] = msg.users
			rooms[msg.room]["joined"] = msg.numusers

		else:
			rooms[msg.room]["users"] = msg.users
			rooms[msg.room]["joined"] = msg.numusers
		#self.PrivateRoomsOwned[msg.room]["users"] = msg.users
		self.SetPrivateRooms()
		#msg.debug()
		
	def PrivateRoomOwned(self, msg):
		rooms = self.PrivateRooms
		if msg.room not in rooms:
			self.CreatePrivateRoom(msg.room)
			rooms[msg.room]["operators"] = msg.operators
		else:
			rooms[msg.room]["operators"] = msg.operators
		
		#msg.debug()
		
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
			#rooms[room]["operator"] = True
			self.frame.logMessage(_("You have been added to a private room: %(room)s") % {"room":room} )
		self.SetPrivateRooms()

		
	def PrivateRoomRemoved(self, msg):
		rooms = self.PrivateRooms
		if msg.room in rooms:
			del rooms[msg.room]
		self.SetPrivateRooms()
		
	def TogglePrivateRooms(self, enabled):
		self.frame.np.config.sections["server"]["private_chatrooms"] = enabled
		self.Menu_PrivateRoom_Enable.set_sensitive(not enabled)
		self.Menu_PrivateRoom_Disable.set_sensitive(enabled)
		self.Menu_PrivateRoom_Create.set_sensitive(enabled)
		
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
		if user not in self.frame.np.users:
			self.frame.np.queue.put(slskmessages.GetPeerAddress(user))
		elif self.frame.np.users[user].addr is None:
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
				#print "ignored message from IP:", ip, msg.user
				return
		self.joinedrooms[msg.room].SayChatRoom(msg, text)
	def PublicRoomMessage(self, msg, text):
		try:
			room = self.joinedrooms['Public ']
		except KeyError:
			return
		#msg.user = "%s | %s" % (msg.room, msg.user)
		room.SayChatRoom(msg, text, public=True)
	
	def UpdateColours(self):
		self.frame.SetTextBG(self.frame.roomlist.RoomsList)
		self.frame.SetTextBG(self.frame.roomlist.CreateRoomEntry)
		self.frame.SetTextBG(self.frame.roomlist.SearchRooms)

		for room in self.joinedrooms.values():
			room.ChangeColours()
			
	def saveColumns(self):
		for room in self.frame.np.config.sections["columns"]["chatrooms"].keys()[:]:
			if room not in self.joinedrooms:
				del self.frame.np.config.sections["columns"]["chatrooms"][room]
		for room in self.joinedrooms.values():
			room.saveColumns()
		

	def LeaveRoom(self, msg):
		room = self.joinedrooms[msg.room]
		if room.logfile is not None:
			room.logfile.close()
			room.logfile = None
		if self.frame.ChatNotebook.is_tab_detached(room.Main):
			self.frame.ChatNotebook.attach_tab(room.Main)
		self.frame.ChatNotebook.remove_page(room.Main)
		room.destroy()
		del self.joinedrooms[msg.room]
		if msg.room[-1:] != ' ': # meta rooms
			self.frame.RoomSearchCombo_List.remove(self.frame.searchroomslist[msg.room])
		if self.joinedrooms == {} and not self.frame.show_room_list1.get_active():
			win = OptionDialog(self.frame, _("You aren't in any chat rooms.") + " " + _("Open Room List?"), modal=True, status=None, option=False, third="")
			win.connect("response", self.frame.onOpenRoomList)
			win.set_title(_("Nicotine+")+": "+_("Open Room List?"))
			win.set_icon( self.frame.images["n"])
			win.show()
			
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
				clist += [i[0] for i in self.frame.userlist.userlist]
			if config["aliases"]:
				clist += ["/"+k for k in self.frame.np.config.aliases.keys()]
			if config["commands"]:
				clist += self.CMDS
			self.clist = clist
		
		for room in self.joinedrooms.values():
			room.GetCompletionList(clist=list(self.clist))
			
def TickDialog(parent, default = ""):
	dlg = gtk.Dialog(title = _("Set ticker message"), parent = parent,
		buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OK, gtk.RESPONSE_OK))
	dlg.set_default_response(gtk.RESPONSE_OK)
	
	t = 0
	
	dlg.set_border_width(10)
	dlg.vbox.set_spacing(10)
		
	l = gtk.Label(_("Set room ticker message:"))
	l.set_alignment(0, 0.5)
	dlg.vbox.pack_start(l, False, False)
	
	entry = gtk.Entry()
	entry.set_activates_default(True)
	entry.set_text(default)
	dlg.vbox.pack_start(entry, True, True)

	h = gtk.HBox(False, False)
	r1 = gtk.RadioButton()
	r1.set_label(_("Just this time"))
	r1.set_active(True)
	h.pack_start(r1, False, False)
	
	r2 = gtk.RadioButton(r1)
	r2.set_label(_("Always for this channel"))
	h.pack_start(r2, False, False)
	
	r3 = gtk.RadioButton(r1)
	r3.set_label(_("Default for all channels"))
	h.pack_start(r3, False, False)
	
	dlg.vbox.pack_start(h, True, True)
	
	dlg.vbox.show_all()

	result = None
	if dlg.run() == gtk.RESPONSE_OK:
		if r1.get_active():
			t = 0
		elif r2.get_active():
			t = 1
		elif r3.get_active():
			t = 2
		bytes = entry.get_text()
		try:
			result = unicode(bytes, "UTF-8")
		except UnicodeDecodeError:
			log.addwarning("We have a problem, PyGTK get_text does not seem to return UTF-8. Please file a bug report.")
			result = unicode(bytes, "UTF-8", "replace")
	dlg.destroy()
	return [t, result]

class ChatRoom:
	def __init__(self, roomsctrl, room, users, meta = False):
		self.roomsctrl = roomsctrl
		self.frame = roomsctrl.frame
		#self.tooltips = self.frame.tooltips

		gtk.glade.set_custom_handler(self.get_custom_widget)
		
		self.wTree = gtk.glade.XML(os.path.join(os.path.dirname(os.path.realpath(__file__)), "chatrooms.glade" ), None, 'nicotine' ) 
		widgets = self.wTree.get_widget_prefix("")
		for i in widgets:
			name = gtk.glade.get_widget_name(i)
			self.__dict__[name] = i
		self.ChatRoomTab.remove(self.Main)
		self.ChatRoomTab.destroy()
	
		self.wTree.signal_autoconnect(self)
		
		#if not self.frame.np.config.sections["ui"]["tooltips"]:
		#	self.tooltips.disable()
		self.room = room
		self.lines = []
		self.logfile = None
		self.leaving = 0
		self.meta = meta # not a real room if set to True
		config = self.frame.np.config.sections
		if not config["ticker"]["hide"]:
			self.Ticker.show()
		
		self.OnShowChatButtons(show=(not config["ui"]["chat_hidebuttons"]))
			
		if self.frame.translux:
			self.tlux_roomlog = lambda: self.RoomLog.get_window(gtk.TEXT_WINDOW_TEXT)
			self.tlux_chat = lambda: self.ChatScroll.get_window(gtk.TEXT_WINDOW_TEXT)
			self.frame.translux.subscribe(self.RoomLog, self.tlux_roomlog)
			self.frame.translux.subscribe(self.ChatScroll, self.tlux_chat)
			self.RoomLog.get_parent().get_vadjustment().connect("value-changed", lambda *args: self.RoomLog.queue_draw())
			self.ChatScroll.get_parent().get_vadjustment().connect("value-changed", lambda *args: self.ChatScroll.queue_draw())
			self.ChatScroll.get_parent().get_hadjustment().connect("value-changed", lambda *args: self.ChatScroll.queue_draw())
		self.clist = []
		self.Elist = {}
		self.encoding, m = EncodingsMenu(self.frame.np, "roomencoding", room)
		self.EncodingStore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
		self.Encoding.set_size_request(100, -1)
		self.Encoding.set_model(self.EncodingStore)
		cell = gtk.CellRendererText()
		self.Encoding.pack_start(cell, True)
		self.Encoding.add_attribute(cell, 'text', 0)
		cell2 = gtk.CellRendererText()
		self.Encoding.pack_start(cell2, False)
		self.Encoding.add_attribute(cell2, 'text', 1)
	
		for item in m:
			self.Elist[item[1]] = self.EncodingStore.append([item[1], item[0] ])
			if self.encoding == item[1]:
				self.Encoding.set_active_iter(self.Elist[self.encoding])

		self.Ticker.entry.connect("button_press_event", self.OnTickerClicked)
		self.Ticker.entry.connect("focus-in-event", self.OnTickerFocus)
		self.Ticker.entry.connect("focus-out-event", self.OnTickerFocus)
		
		if self.frame.SEXY and config["ui"]["spellcheck"]:
			import sexy
			self.ChatEntryBox.remove(self.ChatEntry)
			self.ChatEntry.destroy()
			self.ChatEntry = sexy.SpellEntry()
			self.ChatEntry.show()
			self.ChatEntry.connect("activate", self.OnEnter)
			
			self.ChatEntry.connect("key_press_event", self.OnKeyPress)
			self.ChatEntryBox.pack_start(self.ChatEntry, True, True, 0)
			
		
		self.midwaycompletion = False # True if the user just used tab completion
		self.completions = {} # Holds temp. information about tab completoin
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
		statusiconwidth = self.frame.images["offline"].get_width()+4
		self.cols = cols = InitialiseColumns(self.UserList, 
			[_("Status"), statusiconwidth, "pixbuf"],
			[_("Country"), 25, "pixbuf"],
			[_("User"), 100, "text", self.UserColumnDraw],
			[_("Speed"), 0, "number", self.frame.CellDataFunc],
			[_("Files"), 0, "number", self.frame.CellDataFunc],
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
		if len(config["columns"]["chatrooms"][room]) != 5:	# Insert new column to old settings.
			config["columns"]["chatrooms"][room].insert(1, 1)
		for i in range (5):
			parent = cols[i].get_widget().get_ancestor(gtk.Button)
			if parent:
				parent.connect('button_press_event', PressHeader)
			# Read Show / Hide column settings from last session
			cols[i].set_visible(config["columns"]["chatrooms"][room][i])
		if config["columns"]["hideflags"]:
			cols[1].set_visible(0)
			config["columns"]["chatrooms"][room][1] = 0
		self.users = {}

		self.usersmodel = gtk.ListStore(gtk.gdk.Pixbuf, gtk.gdk.Pixbuf, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT, gobject.TYPE_INT, gobject.TYPE_INT, gobject.TYPE_STRING)

		for (username, user) in users.iteritems():
			img = self.frame.GetStatusImage(user.status)
			flag = user.country
			if flag is not None:
				flag = "flag_"+flag
				self.frame.flag_users[username] = flag
			else:
				flag = self.frame.GetUserFlag(username)
			hspeed = HumanSpeed(user.avgspeed)
			hfiles = Humanize(user.files)
			iter = self.usersmodel.append([img, self.frame.GetFlagImage(flag), username, hspeed, hfiles, user.status, user.avgspeed, user.files, flag])
			self.users[username] = iter
			self.roomsctrl.GetUserAddress(username)
		self.usersmodel.set_sort_column_id(2, gtk.SORT_ASCENDING)
		
		self.UpdateColours()
		self.UserList.set_model(self.usersmodel)
		self.UserList.enable_model_drag_source(gtk.gdk.BUTTON1_MASK, [('text/plain', 0, 2)], gtk.gdk.ACTION_COPY)
		self.UserList.connect("drag_data_get", self.drag_data_get_data)
		self.UserList.set_property("rules-hint", True)
		self.popup_menu_privaterooms = PopupMenu(self.frame)
		self.popup_menu = popup = PopupMenu(self.frame)
		popup.setup(
			("USER", "", popup.OnCopyUser),
			("", None),
			("#" + _("Send _message"), popup.OnSendMessage, gtk.STOCK_EDIT),
			("", None),
			("#" + _("Show IP a_ddress"), popup.OnShowIPaddress, gtk.STOCK_NETWORK),
			("#" + _("Get user i_nfo"), popup.OnGetUserInfo, gtk.STOCK_DIALOG_INFO),
			("#" + _("Brow_se files"), popup.OnBrowseUser, gtk.STOCK_HARDDISK),
			("#" + _("Gi_ve privileges"), popup.OnGivePrivileges, gtk.STOCK_JUMP_TO),
			("", None),
			("$" + _("_Add user to list"), popup.OnAddToList),
			("$" + _("_Ban this user"), popup.OnBanUser),
			("$" + _("_Ignore this user"), popup.OnIgnoreUser),
			("$" + _("B_lock this user's IP Address"), popup.OnBlockUser),
			("$" + _("Ignore this user's IP Address"), popup.OnIgnoreIP),
			("", None),
			("#" + _("Sear_ch this user's files"), popup.OnSearchUser, gtk.STOCK_FIND),
			(1, _("Private rooms"), self.popup_menu_privaterooms, self.OnPrivateRooms),
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
		img = gtk.Image()
		img.set_from_pixbuf(self.frame.images["money"])
		self.Menu_GivePrivileges.set_image(img)
		self.UserList.connect("button_press_event", self.OnPopupMenu)

		self.ChatEntry.grab_focus()
		self.ChatEntryBox.set_focus_child(self.ChatEntry)
		
		self.logpopupmenu = PopupMenu(self.frame).setup(
			("#" + _("Find"), self.OnFindLogWindow, gtk.STOCK_FIND),
			("", None),
			("#" + _("Copy"), self.OnCopyRoomLog, gtk.STOCK_COPY),
			("#" + _("Copy All"), self.OnCopyAllRoomLog, gtk.STOCK_COPY),
			("", None),
			("#" + _("Clear log"), self.OnClearRoomLog, gtk.STOCK_CLEAR),
		)
		self.RoomLog.connect("button-press-event", self.OnPopupRoomLogMenu)
		
		self.chatpopmenu = PopupMenu(self.frame).setup(
			("#" + _("Find"), self.OnFindChatLog, gtk.STOCK_FIND),
			("", None),
			("#" + _("Copy"), self.OnCopyChatLog, gtk.STOCK_COPY),
			("#" + _("Copy All"), self.OnCopyAllChatLog, gtk.STOCK_COPY),
			("", None),
			("#" + _("Clear log"), self.OnClearChatLog, gtk.STOCK_CLEAR),
		)
		self.ChatScroll.connect("button-press-event", self.OnPopupChatRoomMenu)
		self.buildingcompletion = False
		self.GetCompletionList(clist=list(self.roomsctrl.clist))
		if config["logging"]["readroomlogs"]:
			self.ReadRoomLogs()
		self.CountUsers()

	def RoomStatus(self, column, cellrenderer, model, iter):

		cellrenderer.set_property("weight", colour)
		
	def ReadRoomLogs(self):
		config = self.frame.np.config.sections
		log = os.path.join(config["logging"]["roomlogsdir"], fixpath(self.room.replace(os.sep, "-")) + ".log")
		try:
			roomlines = int(config["logging"]["readroomlines"])
		except:
			roomlines = 15
		try:
			encodings = ['UTF-8'] # New style logging, always in UTF-8
			try:
				encodings.append(config["server"]["roomencoding"][self.room]) # Old style logging, room dependent
			except KeyError:
				pass
			f = open(log, "r")
			logfile = f.read()
			f.close()
			loglines = logfile.split("\n")
			for bytes in loglines[ - roomlines : -1 ]:
				l = findBestEncoding(bytes, encodings)
				# Try to parse line for username
				if len(l) > 20 and l[10].isspace() and l[11].isdigit() and l[20] in ("[", "*"):
					line = l[11:]
					if l[20] == "[" and l[20:].find("] ") != -1:
						namepos = l[20:].find("] ")
						user = l[21:20+namepos].strip()
						user = user.encode('UTF-8') # this could go screwy! But there's no other way without logging raw bytes in the log file
						self.getUserTag(user)
						usertag = self.tag_users[user]
					else:
						user = None
						usertag = None
					if user == config["server"]["login"]:
						tag = self.tag_local
					elif l[20] == "*":
						tag = self.tag_me
					elif l[20+namepos:].upper().find(config["server"]["login"].upper()) > -1:
						tag = self.tag_hilite
					else:
						tag = self.tag_remote
				else:
					line = l
					user = None
					tag = None
					usertag = None
				timestamp_format=self.frame.np.config.sections["logging"]["rooms_timestamp"]

				line = re.sub("\s\s+", "  ", line)
				line += "\n"
				if user != config["server"]["login"]:
					self.lines.append(AppendLine(self.ChatScroll, self.frame.CensorChat(line), tag, username=user, usertag=usertag, timestamp_format=""))
				else:
					self.lines.append(AppendLine(self.ChatScroll, line, tag, username=user, usertag=usertag, timestamp_format=""))
			if len(loglines[ - roomlines : -1 ]) > 0:
				self.lines.append(AppendLine(self.ChatScroll, _("--- old messages above ---"), self.tag_hilite))
			gobject.idle_add(self.frame.ScrollBottom, self.ChatScroll.get_parent())
		except IOError, e:
			pass

	def on_key_press_event(self, widget, event):
		key = gtk.gdk.keyval_name(event.keyval)
		# Match against capslock + control and control
		if key in ( "f", "F") and event.state  in (gtk.gdk.CONTROL_MASK, gtk.gdk.LOCK_MASK|gtk.gdk.CONTROL_MASK) :
			self.OnFind(widget)
		elif key in ( "F3"):
			self.OnFind(widget, repeat=True)

	def OnFind(self, widget, repeat=False):
		self.frame.OnFindTextview(None, widget, repeat=repeat)

	def OnFindLogWindow(self, widget):
		self.frame.OnFindTextview(None, self.RoomLog)
		
	def OnFindChatLog(self, widget):
		self.frame.OnFindTextview(None, self.ChatScroll)
		
	def drag_data_get_data(self, treeview, context, selection, target_id, etime):
		treeselection = treeview.get_selection()
		model, iter = treeselection.get_selected()
		user = model.get_value(iter, 2)
		#data = (status, flag, user, speed, files)
		selection.set(selection.target, 8, user)
			
	def get_custom_widget(self, widget, string0, id, string1, string2, int1=None, int2=None, ):
		if id == "Ticker":
			t = Ticker()
			return t
		else:
			return gtk.Label(_("(custom widget: %s)") % id)
			
	def destroy(self):
		if self.frame.translux and self.tlux_roomlog:
			self.frame.translux.unsubscribe(self.tlux_roomlog)
			self.frame.translux.unsubscribe(self.tlux_chat)
		self.Main.destroy()
		
	def OnPrivateRooms(self, widget):
		if self.popup_menu.user == None or self.popup_menu.user == self.frame.np.config.sections["server"]["login"]:
			return False
		user = self.popup_menu.user
		items = []

		popup = self.popup_menu_privaterooms
		popup.clear()
		popup.set_user(self.popup_menu.user)
		#print self.roomsctrl.PrivateRooms
		for room in self.roomsctrl.PrivateRooms:
			if not (self.roomsctrl.IsPrivateRoomOwned(room) or self.roomsctrl.IsPrivateRoomOperator(room)):
				continue
			if user in self.roomsctrl.PrivateRooms[room]["users"]:
				items.append(("#" + _("Remove from private room %s" %room), popup.OnPrivateRoomRemoveUser, gtk.STOCK_REMOVE, room))
			else:
				items.append(("#" + _("Add to private room %s" %room), popup.OnPrivateRoomAddUser, gtk.STOCK_ADD, room))
			if self.roomsctrl.IsPrivateRoomOwned(room):
				if self.popup_menu.user in self.roomsctrl.PrivateRooms[room]["operators"]:
					items.append(("#" + _("Remove as operator of %s" %room), popup.OnPrivateRoomRemoveOperator, gtk.STOCK_REMOVE, room))
				else:
					items.append(("#" + _("Add as operator of %s" %room), popup.OnPrivateRoomAddOperator, gtk.STOCK_ADD, room))

		popup.setup(*items)
		
		return True
		
	def OnPrivateRoomsUser(self, widget, popup=None):
		if popup is None:
			return
		menu = popup
		user = menu.user
		items = menu.get_children()
		
		act = False
		
		return True
	
	def OnPopupMenu(self, widget, event):
		items = self.popup_menu.get_children()
		d = self.UserList.get_path_at_pos(int(event.x), int(event.y))
		if not d:
			return
		path, column, x, y = d
		user = self.usersmodel.get_value(self.usersmodel.get_iter(path), 2)
		
		# Double click starts a private message
		if event.button != 3:
			if event.type == gtk.gdk._2BUTTON_PRESS:
				self.frame.privatechats.SendMessage(user, None, 1)
				self.frame.ChangeMainPage(None, "private")
			return
		self.popup_menu.editing = True
		self.popup_menu.set_user(user)
		me = (self.popup_menu.user == None or self.popup_menu.user == self.frame.np.config.sections["server"]["login"])
		
		#self.Menu_SendMessage
		#self.Menu_ShowIPaddress
		#self.Menu_GetUserInfo
		#self.Menu_BrowseUser
		#self.Menu_GivePrivileges

		self.Menu_AddToList.set_active(user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
		self.Menu_BanUser.set_active(user in self.frame.np.config.sections["server"]["banlist"])
		self.Menu_IgnoreUser.set_active(user in self.frame.np.config.sections["server"]["ignorelist"])
		self.Menu_BlockUser.set_active(self.frame.UserIpIsBlocked(user))
		self.Menu_BlockUser.set_sensitive(not me)
		self.Menu_IgnoreIP.set_active(self.frame.UserIpIsIgnored(user))
		self.Menu_IgnoreIP.set_sensitive(not me) 
		#self.Menu_SearchUser
		self.Menu_PrivateRooms.set_sensitive(not me)

		self.popup_menu.editing = False	
		self.popup_menu.popup(None, None, None, event.button, event.time)
		

	
	def OnShowChatHelp(self, widget):
		self.frame.OnAboutChatroomCommands(widget, self.GetTabParent(self.Main))

	def OnShowChatButtons(self, show=True):
		for widget in self.HideStatusLog, self.HideUserList, self.ShowChatHelp:
			if show:
				widget.show()
			else:
				widget.hide()
		if self.frame.np.config.sections["ui"]["speechenabled"] and show:
			self.Speech.show()
		else:
			self.Speech.hide()
				
				
	def OnHideStatusLog(self, widget):
		act = widget.get_active()
		if act:
			self.RoomLogWindow.hide()
			self.HideStatusLogImage.set_from_stock(gtk.STOCK_GO_DOWN, 1)
		else:
			self.RoomLogWindow.show()
			self.HideStatusLogImage.set_from_stock(gtk.STOCK_GO_UP, 1)


	def OnHideUserList(self, widget):
		act = widget.get_active()
		if act:
			self.vbox5.hide()
			self.HideUserListImage.set_from_stock(gtk.STOCK_GO_BACK, 1)
		else:
			self.vbox5.show()
			self.HideUserListImage.set_from_stock(gtk.STOCK_GO_FORWARD, 1)

	
	def TickerSet(self, msg):
		self.Ticker.set_ticker({})
		for user in msg.msgs.keys():
			if user in self.frame.np.config.sections["server"]["ignorelist"] or self.frame.UserIpIsIgnored(user):
				# User ignored, ignore Ticker messages
				return
			self.Ticker.add_ticker(user, msg.msgs[user])

	def TickerAdd(self, msg):
		user = msg.user
		if user in self.frame.np.config.sections["server"]["ignorelist"] or self.frame.UserIpIsIgnored(user):
			# User ignored, ignore Ticker messages
			return
		self.Ticker.add_ticker(msg.user, msg.msg)

	def TickerRemove(self, msg):
		self.Ticker.remove_ticker(msg.user)
		
	def SayChatRoom(self, msg, text, public=False):
		text = re.sub("\s\s+", "  ", text)
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
				self.frame.ChatNotebook.request_hilite(self.Main)
				if self.frame.ChatNotebook.is_tab_detached(self.Main):
					if not self.frame.ChatNotebook.is_detached_tab_focused(self.Main):
						self.frame.Notifications.Add("rooms", user, self.room, tab=False)
				else:
					self.frame.ChatRequestIcon(1, self.Main)
						
					# add hilite to trayicon
					if self.frame.ChatNotebook.get_current_page() != self.frame.ChatNotebook.page_num(self.roomsctrl.joinedrooms[self.room].Main) or self.frame.MainNotebook.get_current_page() != self.frame.MainNotebook.page_num(self.frame.hpaned1) or not self.frame.is_mapped:
						if self.room not in self.frame.TrayApp.tray_status["hilites"]["rooms"]:
							self.frame.Notifications.Add("rooms", user, self.room, tab=True)
				#else:
					#self.MainWindow.set_urgency_hint(False)
			else:
				self.frame.ChatNotebook.request_changed(self.Main)
				if self.frame.ChatNotebook.is_tab_detached(self.Main):
					pass
				else:
					self.frame.ChatRequestIcon(0)

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

		if len(self.lines) >= 400:
			buffer = self.ChatScroll.get_buffer()
			start = buffer.get_start_iter()
			end = buffer.get_iter_at_line(1)
			self.ChatScroll.get_buffer().delete(start, end)
			del self.lines[0]

		line = "\n-- ".join(line.split("\n"))
		if self.Log.get_active():
			self.logfile = WriteLog(self.logfile, self.frame.np.config.sections["logging"]["roomlogsdir"], self.room, line)
		self.getUserTag(user)
		timestamp_format=self.frame.np.config.sections["logging"]["rooms_timestamp"]
		if user != login:
			self.lines.append(AppendLine(self.ChatScroll, self.frame.CensorChat(line), tag, username=user, usertag=self.tag_users[user], timestamp_format=timestamp_format))
			if self.Speech.get_active():
				self.frame.Notifications.new_tts(self.frame.np.config.sections["ui"]["speechrooms"] % {"room": self.room, "user": self.frame.Notifications.tts_clean(user), "message": self.frame.Notifications.tts_clean(speech)} )
		else:
			self.lines.append(AppendLine(self.ChatScroll, line, tag, username=user, usertag=self.tag_users[user], timestamp_format=timestamp_format))
		
			
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
			log.add('Alias "%s" returned nothing' % alias)
			return
		if text[:2] == "//":
			text = text[1:]
		self.frame.np.queue.put(slskmessages.SayChatroom(self.room, ToBeEncoded(self.frame.AutoReplace(text), self.encoding)))

			
	def OnEnter(self, widget):
		bytes = widget.get_text()
		try:
			text = unicode(bytes, "UTF-8")
		except UnicodeDecodeError:
			log.addwarning("We have a problem, PyGTK get_text does not seem to return UTF-8. Please file a bug report.")
			text = unicode(bytes, "UTF-8", "replace")
		if not text:
			widget.set_text("")
			return
		if is_alias(self.frame.np.config.aliases, text):
			import thread
			thread.start_new_thread(self.threadAlias, (text,))
			widget.set_text("")
			return
		
		s = text.split(" ", 1) # string
		cmd = s[0]
		if len(s) == 2:
			args = s[1]
		else:
			args = ""
		s = bytes.split(" ", 1) # bytes
		if len(s) == 2:
			byteargs = s[1]
		else:
			byteargs = ""

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
		elif cmd == "/nsa":
			if byteargs:
				self.frame.LocalUserInfoRequest(byteargs)
				self.frame.BrowseUser(byteargs)
				self.frame.OnUserInfo(None)
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
				user = byteargs.split(" ", 1)[0]
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
		elif cmd == "/nuke":
			if byteargs:
				self.frame.BanUser(byteargs)
				self.frame.IgnoreUser(byteargs)
		elif cmd == "/unban":
			if byteargs:
				self.frame.UnbanUser(byteargs)
		elif cmd == "/unignore":
			if byteargs:
				self.frame.UnignoreUser(byteargs)
		elif cmd in ["/clear", "/cl"]:
			self.ChatScroll.get_buffer().set_text("")
			self.lines = []
		elif cmd in ["/a", "/away"]:
			self.frame.OnAway(None)
		elif cmd in ["/q", "/quit", "/exit"]:
			self.frame.OnExit(None)
			return # Avoid gsignal warning
		elif cmd == "/now":
			self.NowPlayingThread()
		elif cmd == "/detach":
			self.Detach()
		elif cmd == "/attach":
			self.frame.ChatNotebook.attach_tab(self.Main)
			gobject.idle_add(self.frame.ScrollBottom, self.ChatScroll.get_parent())
		elif cmd == "/rescan":
			self.frame.BothRescan()
		elif cmd in ["/tick", "/t"]:
			self.frame.np.queue.put(slskmessages.RoomTickerSet(self.room, ToBeEncoded(args, self.encoding)))
		elif cmd in ("/tickers",):
			self.showTickers()
		#elif cmd in ('/reload',):
			#self.frame.pluginhandler.reread()
			#self.frame.pluginhandler = pluginsystem.PluginHandler(self.frame)
		elif cmd[:1] == "/" and self.frame.pluginhandler.TriggerPublicCommandEvent(self.room, cmd[1:], args):
			pass
		elif cmd and cmd[:1] == "/" and cmd != "/me" and cmd[:2] != "//":
			self.frame.logMessage(_("Command %s is not recognized") % text)
			return
		else:
			if text[:2] == "//":
				text = text[1:]
			tuple = self.frame.pluginhandler.OutgoingPublicChatEvent(self.room, text)
			if tuple != None:
				(r, text) = tuple
				self.Say(self.frame.AutoReplace(text))
				self.frame.pluginhandler.OutgoingPublicChatNotification(self.room, text)
			#else:
			#	self.frame.logMessage(_("Pluginsystem decided to shut me up"))
		self.ChatEntry.set_text("")
	
	def showTickers(self):
		tickers = self.Ticker.get_tickers()
		header = _("All ticker messages for %(room)s:") % {'room':self.room}
		self.frame.logMessage("%s\n%s" % (header, "\n".join(["%s: %s" % (user, msg) for (user, msg) in tickers])))
	def Detach(self, widget = None):
		self.frame.ChatNotebook.detach_tab(self.Main, _("Nicotine+ Chatroom: %s") % self.room)
		gobject.idle_add(self.frame.ScrollBottom, self.ChatScroll.get_parent())
		
	def Say(self, text):
		text = re.sub("\s\s+", "  ", text)
		tobeencoded = ToBeEncoded(text, self.encoding)
		self.frame.np.queue.put(slskmessages.SayChatroom(self.room, tobeencoded))
		
	def NowPlayingThread(self):
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
			flag = "flag_"+flag
			self.frame.flag_users[username] = flag
		else:
			flag = self.frame.GetUserFlag(username)
		hspeed = HumanSpeed(userdata.avgspeed)
		hfiles = Humanize(userdata.files)
		self.users[username] = self.usersmodel.append([img, self.frame.GetFlagImage(flag), username, hspeed, hfiles, userdata.status, userdata.avgspeed, userdata.files, flag])
		self.getUserTag(username)

		self.CountUsers()
		
	def UserLeftRoom(self, username):
		if username not in self.users:
			return
		# Remove from completion list, and completion drop-down
		if self.frame.np.config.sections["words"]["tab"]:
			if username in self.clist and username not in [i[0] for i in self.frame.userlist.userlist]:
				self.clist.remove(username)
				if self.frame.np.config.sections["words"]["dropdown"]:
					liststore = self.ChatEntry.get_completion().get_model()
					iter = liststore.get_iter_root()
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
		numusers = len(self.users.keys())
		if numusers > 1:
			self.LabelPeople.show()
			self.LabelPeople.set_text(_("%i people in room") % numusers)
		elif numusers == 1:
			self.LabelPeople.show()
			self.LabelPeople.set_text(_("You are alone"))
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




	def UserColumnDraw(self, column, cellrenderer, model, iter):
		user = self.usersmodel.get_value(iter, 2)
		if self.room in self.roomsctrl.PrivateRooms:
			if user == self.roomsctrl.PrivateRooms[self.room]["owner"]:
				cellrenderer.set_property("underline", pango.UNDERLINE_SINGLE)
				cellrenderer.set_property("weight", pango.WEIGHT_BOLD)
			elif user in (self.roomsctrl.PrivateRooms[self.room]["operators"]):
				cellrenderer.set_property("weight", pango.WEIGHT_BOLD)
				cellrenderer.set_property("underline", pango.UNDERLINE_NONE)
			else:
				cellrenderer.set_property("weight", pango.WEIGHT_NORMAL)
				cellrenderer.set_property("underline", pango.UNDERLINE_NONE)
		else:
				cellrenderer.set_property("weight", pango.WEIGHT_NORMAL)
				cellrenderer.set_property("underline", pango.UNDERLINE_NONE)

		self.frame.CellDataFunc(column, cellrenderer, model, iter)

	def GetUserHeirarchy(self, user):
		if user not in self.users:
			return
		self.usersmodel.set(self.users[user], 3, HumanSpeed(avgspeed), 4, Humanize(files), 6, avgspeed, 7, files)

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
		
		if colour:
			tag = buffer.create_tag(foreground = colour, font=font)
		else:
			tag = buffer.create_tag( font=font)
		if username is not None:
			usernamestyle = self.frame.np.config.sections["ui"]["usernamestyle"]
			
			if usernamestyle == "bold":
				tag.set_property("weight", pango.WEIGHT_BOLD)
			else:
				tag.set_property("weight", pango.WEIGHT_NORMAL)
			if usernamestyle == "italic":
				tag.set_property("style", pango.STYLE_ITALIC)
			else:
				tag.set_property("style", pango.STYLE_NORMAL)
			if usernamestyle == "underline":
				tag.set_property("underline", pango.UNDERLINE_SINGLE)
			else:
				tag.set_property("underline", pango.UNDERLINE_NONE)
				
			tag.connect("event", self.UserNameEvent, username)
			tag.last_event_type = -1
		return tag
		
	def UserNameEvent(self, tag, widget, event, iter, user):

		if tag.last_event_type == gtk.gdk.BUTTON_PRESS and event.type == gtk.gdk.BUTTON_RELEASE and event.button in (1, 2):
			#items = self.popup_menu.get_children()
			# Chat, Userlists use the normal popup system
			self.popup_menu.editing = True
			self.popup_menu.set_user(user)
			me = (self.popup_menu.user == None or self.popup_menu.user == self.frame.np.config.sections["server"]["login"])
			

			#self.Menu_SendMessage
			#self.Menu_ShowIPaddress
			#self.Menu_GetUserInfo
			#self.Menu_BrowseUser
			#self.Menu_GivePrivileges

			self.Menu_AddToList.set_active(user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
			self.Menu_BanUser.set_active(user in self.frame.np.config.sections["server"]["banlist"])
			self.Menu_IgnoreUser.set_active(user in self.frame.np.config.sections["server"]["ignorelist"])
			self.Menu_BlockUser.set_active(self.frame.UserIpIsBlocked(user))
			self.Menu_BlockUser.set_sensitive(not me)
			self.Menu_IgnoreIP.set_active(self.frame.UserIpIsIgnored(user))
			self.Menu_IgnoreIP.set_sensitive(not me) 
			#self.Menu_SearchUser
			self.Menu_PrivateRooms.set_sensitive(not me)

			self.popup_menu.editing = False
			self.popup_menu.popup(None, None, None, event.button, event.time)
		tag.last_event_type = event.type
		
	def UpdateColours(self):
		self.frame.ChangeListFont(self.UserList, self.frame.np.config.sections["ui"]["listfont"])
		map = self.ChatScroll.get_style().copy()
		self.backupcolor = map.text[gtk.STATE_NORMAL]
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
		
		self.frame.SetTextBG(self.ChatScroll)
		self.frame.SetTextBG(self.RoomLog)
		self.frame.SetTextBG(self.UserList)
		
		self.frame.SetTextBG(self.ChatEntry)
		self.frame.SetTextBG(self.AutoJoin)
		self.frame.SetTextBG(self.Log)
		self.frame.SetTextBG(self.Ticker.entry)
		
		
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
		if colour in self.frame.np.config.sections["ui"]:
			color = self.frame.np.config.sections["ui"][colour]
		else:
			color = ""
		font = self.frame.np.config.sections["ui"]["chatfont"]
		
		if color == "":
			color = self.backupcolor
		else:
			color = gtk.gdk.color_parse(color)
		tag.set_property("foreground-gdk", color)
		tag.set_property("font", font)
		# Hotspots
		if colour in ["useraway", "useronline", "useroffline"]:
			usernamestyle = self.frame.np.config.sections["ui"]["usernamestyle"]
			if usernamestyle == "bold":
				tag.set_property("weight", pango.WEIGHT_BOLD)
			else:
				tag.set_property("weight", pango.WEIGHT_NORMAL)
			if usernamestyle == "italic":
				tag.set_property("style", pango.STYLE_ITALIC)
			else:
				tag.set_property("style", pango.STYLE_NORMAL)
			if usernamestyle == "underline":
				tag.set_property("underline", pango.UNDERLINE_SINGLE)
			else:
				tag.set_property("underline", pango.UNDERLINE_NONE)
		
			
	def ChangeColours(self):
		
		map = self.ChatScroll.get_style().copy()
		self.backupcolor = map.text[gtk.STATE_NORMAL]
			
		self.changecolour(self.tag_remote, "chatremote")
		self.changecolour(self.tag_local, "chatlocal")
		self.changecolour(self.tag_me, "chatme")
		self.changecolour(self.tag_hilite, "chathilite")
		self.changecolour(self.tag_log, "chatremote")

		for user in self.tag_users:
			self.getUserTag(user)

		self.frame.SetTextBG(self.ChatScroll)
		self.frame.SetTextBG(self.RoomLog)
		self.frame.SetTextBG(self.UserList)
		self.frame.SetTextBG(self.ChatEntry)
		self.frame.SetTextBG(self.AutoJoin)
		self.frame.SetTextBG(self.Log)
		self.frame.SetTextBG(self.Ticker.entry)
		self.frame.ChangeListFont(self.UserList, self.frame.np.config.sections["ui"]["listfont"])
				
	def OnLeave(self, widget = None):
		if self.leaving:
			return
		self.Leave.set_sensitive(False)
		self.leaving = 1
		config = self.frame.np.config.sections
		if self.room in config["columns"]["chatrooms"]:
			del config["columns"]["chatrooms"][self.room]
		if not self.meta:
			self.frame.np.queue.put(slskmessages.LeaveRoom(self.room))
		else:
			if self.room == 'Public ':
				self.frame.np.queue.put(slskmessages.LeavePublicRoom())
				self.roomsctrl.LeaveRoom(slskmessages.LeaveRoom(self.room)) # Faking protocol msg
			else:
				print "Unknown meta chatroom closed."
		self.frame.pluginhandler.LeaveChatroomNotification(self.room)
	def saveColumns(self):
		columns = []
		for column in self.UserList.get_columns():
			columns.append(column.get_visible())
		self.frame.np.config.sections["columns"]["chatrooms"][self.room] = columns
		
		
	def ConnClose(self):
		AppendLine(self.ChatScroll, _("--- disconnected ---"), self.tag_hilite)
		self.usersmodel.clear()
		self.UserList.set_sensitive(False)
		self.users.clear()
		self.CountUsers()
		config = self.frame.np.config.sections
		if not self.AutoJoin.get_active() and self.room in config["columns"]["chatrooms"]:
			del config["columns"]["chatrooms"][self.room]
			
		for tag in self.tag_users.values():
			self.changecolour(tag, "useroffline")
		self.Ticker.set_ticker({})
	def Rejoined(self, users):
		# Update user list with an inexpensive sorting function
		self.usersmodel.set_default_sort_func(lambda *args: -1)
		self.usersmodel.set_sort_column_id(-1, gtk.SORT_ASCENDING)
		for (username, user) in users.iteritems():
			if username in self.users:
				self.usersmodel.remove(self.users[username])
			img = self.frame.GetStatusImage(user.status)
			flag = user.country
			if flag is not None:
				flag = "flag_"+flag
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
		self.usersmodel.set_sort_column_id(2, gtk.SORT_ASCENDING)
		self.usersmodel.set_default_sort_func(None)
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
			if not self.room in autojoin:
				autojoin.append(self.room)
		self.frame.np.config.writeConfiguration()
		

	def GetCompletionList(self, ix=0, text="", clist=[]):
	
		completion = self.ChatEntry.get_completion()
		liststore = completion.get_model()
		liststore.clear()
		self.clist = []
		config = self.frame.np.config.sections["words"]
		completion.set_popup_single_match(not config["onematch"])
		completion.set_minimum_key_length(config["characters"])
		
		if not config["tab"]:
			return
		
		if config["roomusers"]:
			clist += list(self.users.keys())

		# no duplicates
		def _combilower(x):
			try:
				return str.lower(x)
			except:
				return unicode.lower(x)
		clist = list(set(clist))
		clist.sort(key=_combilower)
		completion.set_popup_completion(False)
		if config["dropdown"]:
			for word in clist:
				liststore.append([word])
			completion.set_popup_completion(True)
		self.clist = clist
		
		
	def OnKeyPress(self, widget, event):
		if event.keyval == gtk.gdk.keyval_from_name("Prior"):
			scrolled = self.ChatScroll.get_parent()
			adj = scrolled.get_vadjustment()
			adj.set_value(adj.value - adj.page_increment)
		elif event.keyval == gtk.gdk.keyval_from_name("Next"):
			scrolled = self.ChatScroll.get_parent()
			adj = scrolled.get_vadjustment()
			max = adj.upper - adj.page_size
			new = adj.value + adj.page_increment
			if new > max:
				new = max
			adj.set_value(new)
		# ISO_Left_Tab normally corresponds with shift+tab
		if event.keyval not in (gtk.gdk.keyval_from_name("Tab"), gtk.gdk.keyval_from_name("ISO_Left_Tab")):
			if event.keyval not in (gtk.gdk.keyval_from_name("Shift_L"), gtk.gdk.keyval_from_name("Shift_R")):
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
				direction = 1 # Forward cycle
				if event.keyval == gtk.gdk.keyval_from_name("ISO_Left_Tab"):
					direction = -1 # Backward cycle
				self.completions['currentindex'] = (self.completions['currentindex'] + direction) % len(self.completions['completions'])

				newnick = self.completions['completions'][self.completions['currentindex']]
				widget.insert_text(newnick, preix)
				widget.set_position(preix + len(newnick))
		widget.emit_stop_by_name("key_press_event")
		return True

	def OnTooltip(self, widget, x, y, keyboard_mode, tooltip):
		return showCountryTooltip(widget, x, y, tooltip, 8)
	def OnLogToggled(self, widget):
		if not widget.get_active():
			if self.logfile is not None:
				self.logfile.close()
				self.logfile = None
			if self.room in self.frame.np.config.sections["logging"]["rooms"]:
				self.frame.np.config.sections["logging"]["rooms"].remove(self.room)
		elif widget.get_active():
			if self.room not in self.frame.np.config.sections["logging"]["rooms"]:
				self.frame.np.config.sections["logging"]["rooms"].append(self.room)
		
	def OnEncodingChanged(self, widget):
		try:
			# PyGTK 2.6
			encoding = self.Encoding.get_active_text()
		except:
			# PyGTK 2.4
			iter = self.Encoding.get_active_iter()
			encoding_model = self.Encoding.get_model()
			encoding = encoding_model.get_value(iter, 0)
		if encoding != self.encoding:
			self.encoding = encoding
			SaveEncoding(self.frame.np, "roomencoding", self.room, self.encoding)
	
	def OnPopupChatRoomMenu(self, widget, event):
		if event.button != 3:
			return False
		widget.emit_stop_by_name("button-press-event")
		self.chatpopmenu.popup(None, None, None, event.button, event.time)
		return True
	
	def OnPopupRoomLogMenu(self, widget, event):
		if event.button != 3:
			return False
		widget.emit_stop_by_name("button-press-event")
		self.logpopupmenu.popup(None, None, None, event.button, event.time)
		return True
	
	def OnCopyAllRoomLog(self, widget):
		start, end = self.RoomLog.get_buffer().get_bounds()
		log = self.RoomLog.get_buffer().get_text(start, end)
		self.frame.clip.set_text(log)
		
	def OnCopyRoomLog(self, widget):
		bound = self.RoomLog.get_buffer().get_selection_bounds()
		if bound is not None and len(bound) == 2:
			start, end = bound
			log = self.RoomLog.get_buffer().get_text(start, end)
			self.frame.clip.set_text(log)
			
	def OnCopyChatLog(self, widget):
		bound = self.ChatScroll.get_buffer().get_selection_bounds()
		if bound is not None and len(bound) == 2:
			start, end = bound
			log = self.ChatScroll.get_buffer().get_text(start, end)
			self.frame.clip.set_text(log)
		
	def OnCopyAllChatLog(self, widget):
		start, end = self.ChatScroll.get_buffer().get_bounds()
		log = self.ChatScroll.get_buffer().get_text(start, end)
		self.frame.clip.set_text(log)
		
	def OnClearChatLog(self, widget):
		self.ChatScroll.get_buffer().set_text("")
		self.lines = []

	def OnClearRoomLog(self, widget):
		self.RoomLog.get_buffer().set_text("")

	def OnTickerFocus(self, widget, event):
		if widget.is_focus():
			self.Ticker.disable()
		else:
			self.Ticker.enable()
			
	def GetTabParent(self, page):
		if self.frame.ChatNotebook.is_tab_detached(page):
			return self.Main.get_parent().get_parent()
		return self.frame.MainWindow
		
	def OnTickerClicked(self, widget, event):
		if event.button != 1 or event.type != gtk.gdk._2BUTTON_PRESS:
			return False
		config = self.frame.np.config.sections
		if config["server"]["login"] in self.Ticker.messages:
			old = self.Ticker.messages[config["server"]["login"]]
		else:
			old = ""
		t, result = TickDialog(self.GetTabParent(self.Main), old)
		if not result is None:
			if t == 1:
				if not result:
					if self.room in config["ticker"]["rooms"]:
						del config["ticker"]["rooms"][self.room]
				else:
					config["ticker"]["rooms"][self.room] = result
				self.frame.np.config.writeConfiguration()
			elif t == 2:
				if self.room in config["ticker"]["rooms"]:
					del config["ticker"]["rooms"][self.room]
				config["ticker"]["default"] = result
				self.frame.np.config.writeConfiguration()
			self.frame.np.queue.put(slskmessages.RoomTickerSet(self.room, ToBeEncoded(result, self.encoding)))
		return True

	def ShowTicker(self, visible):
		if visible:
			self.Ticker.enable()
			self.Ticker.show()
		else:
			self.Ticker.disable()
			self.Ticker.hide()

class ChatRooms(IconNotebook):
	def __init__(self, frame):
		self.frame = frame
		ui = self.frame.np.config.sections["ui"]
		IconNotebook.__init__(self, self.frame.images, ui["labelrooms"], ui["tabclosers"], ui["tab_icons"], ui["tab_reorderable"])
		self.roomsctrl = RoomsControl(frame, self)
		
		
		self.popup_enable()
		self.set_tab_pos(self.frame.getTabPosition(self.frame.np.config.sections["ui"]["tabrooms"]))
		
		
	def TabPopup(self, room):
		if room not in self.roomsctrl.joinedrooms:
			return
		popup = PopupMenu(self.frame)
		popup.setup(
			("#" + _("Detach this tab"), self.roomsctrl.joinedrooms[room].Detach, gtk.STOCK_REDO),
			("#" + _("Leave this room"), self.roomsctrl.joinedrooms[room].OnLeave, gtk.STOCK_CLOSE),
		)
		popup.set_user(room)
		
	
		return popup
		
	def on_tab_click(self, widget, event, child):
		if event.type == gtk.gdk.BUTTON_PRESS:
			n = self.page_num(child)
			page = self.get_nth_page(n)
			room = [room for room, tab in self.roomsctrl.joinedrooms.items() if tab.Main is page][0]
			if event.button == 2:
				self.roomsctrl.joinedrooms[room].OnLeave(widget)
				return True
			if event.button == 3:
				menu = self.TabPopup(room)
				menu.popup(None, None, None, event.button, event.time)
				return True
			return False
		return False
	
	def ConnClose(self):
		self.roomsctrl.ConnClose()
