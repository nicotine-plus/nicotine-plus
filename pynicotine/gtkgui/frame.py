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

import os

import gtk
from nicotine_glade import MainWindow, ChatRoomTab, RoomList
from pynicotine.pynicotine import NetworkEventProcessor
from pynicotine import slskmessages
from pynicotine.utils import version
import time

import gobject
import thread
import urllib
import signal
import re
from privatechat import PrivateChats
from chatrooms import ChatRooms
from userinfo import UserTabs, UserInfo
from search import Searches
from downloads import Downloads
from uploads import Uploads
from userlist import UserList
from userbrowse import UserBrowse
from settingswindow import SettingsWindow
from about import *
from checklatest import checklatest
from pynicotine.config import *
import utils, pynicotine.utils
from utils import AppendLine, ImageLabel, IconNotebook, ScrollBottom, PopupMenu, Humanize, popupWarning
import translux
from dirchooser import ChooseFile
from pynicotine.utils import _, ChangeTranslation
import nowplaying
from entrydialog import  *
SEXY=True
try:
	import sexy
except ImportError:
	SEXY=False
	print _("Note: Python Bindings for libsexy were not found. To enable spell checking, get them from http://www.chipx86.com/wiki/Libsexy or your distribution's package manager. Look for sexy-python or python-sexy.")

class roomlist(RoomList):
	def __init__(self, frame):
		RoomList.__init__(self, False)
		self.frame = frame
	
	def OnCreateRoom(self, widget):
		room = widget.get_text()
		if not room:
			return
		self.frame.np.queue.put(slskmessages.JoinRoom(room))
		widget.set_text("")
		
class BuddiesComboBoxEntry(gtk.ComboBoxEntry):
	def __init__(self, frame):
		self.frame = frame
		gtk.ComboBoxEntry.__init__(self)
		self.items = {}
		self.store = gtk.ListStore(gobject.TYPE_STRING)
		self.set_model(self.store)
		self.set_text_column(0)
		self.store.set_default_sort_func(lambda *args: -1) 
		self.store.set_sort_column_id(-1, gtk.SORT_ASCENDING)
		self.show()
		
	def Fill(self):
		self.items.clear()
		self.store.clear()
		self.items[""] = self.store.append([""])
		for user in self.frame.np.config.sections["server"]["userlist"]:
			self.items[user[0]] = self.store.append([user[0]])
		self.store.set_sort_column_id(0, gtk.SORT_ASCENDING)
		
	def Append(self, item):
		if item in self.items:
			return
		self.items[item] = self.get_model().append([item])
		
	def Remove(self, item):
		if item in self.items:
			self.get_model().remove(self.items[item] )
			del self.items[item]
		
		
class NicotineFrame(MainWindow):
	def __init__(self, config, use_trayicon):
		
		self.clip_data = ""
		self.log_queue = []
		self.configfile = config
		self.transfermsgs = {}
		self.transfermsgspostedtime = 0
		self.manualdisconnect = 0
		self.away = 0
		self.showdebug = 0
		self.current_tab = 0
		self.rescanning = 0
		self.brescanning = 0
		self.needrescan = 0
		self.autoaway = False
		self.awaytimer = None
		self.SEXY = SEXY
		self.chatrooms = None
		self.tts = []
		self.tts_playing = self.continue_playing = False

		self.got_focus = False

		try:
			import pynotify
			pynotify.init("Nicotine+")
			self.pynotify = pynotify
		except ImportError:
			self.pynotify = None
			
		self.np = NetworkEventProcessor(self, self.callback, self.logMessage, self.SetStatusText, config)
		config = self.np.config.sections
		
		utils.DECIMALSEP = config["ui"]["decimalsep"]
		utils.CATCH_URLS = config["urls"]["urlcatching"]
		utils.HUMANIZE_URLS = config["urls"]["humanizeurls"]
		utils.PROTOCOL_HANDLERS = config["urls"]["protocols"].copy()
		utils.PROTOCOL_HANDLERS["slsk"] = self.OnSoulSeek
		utils.USERNAMEHOTSPOTS = config["ui"]["usernamehotspots"]
		utils.NICOTINE = self
		pynicotine.utils.log = self.logMessage
		
		self.LoadIcons()
		self.ChangeTranslation = ChangeTranslation
		trerror = ""
		if self.np.config.sections["language"]["setlanguage"]:
			trerror = self.ChangeTranslation(self.np.config.sections["language"]["language"])
		
		self.BuddiesComboEntries = []
		self.roomlist = roomlist(self)
		
		MainWindow.__init__(self)
		self.MainWindow.set_title(_("Nicotine+") + " " + version)
		self.MainWindow.set_icon(self.images["n"])
		self.MainWindow.selection_add_target("PRIMARY", "STRING", 1)
		self.MainWindow.set_geometry_hints(None, min_width=500, min_height=460)
		self.MainWindow.connect("configure_event", self.OnWindowChange)
		
		width = self.np.config.sections["ui"]["width"]
		height = self.np.config.sections["ui"]["height"]
		self.MainWindow.resize(width, height)
		self.MainWindow.set_position(gtk.WIN_POS_CENTER)
		self.MainWindow.show()
		self.minimized = False
	
		self.clip = gtk.Clipboard(display=gtk.gdk.display_get_default(), selection="CLIPBOARD")
		
		
		self.logpopupmenu = PopupMenu(self).setup(
			("#" + _("Find"), self.OnFindLogWindow, gtk.STOCK_FIND),
			("", None),
			("#" + _("Copy"), self.OnCopyLogWindow, gtk.STOCK_COPY),
			("#" + _("Copy All"), self.OnCopyAllLogWindow, gtk.STOCK_COPY),
			("", None),
			("#" + _("Clear log"), self.OnClearLogWindow, gtk.STOCK_CLEAR)
		)
		
		# for iterating buddy changes to the combos
		self.CreateRecommendationsWidgets()


		self.status_context_id = self.Statusbar.get_context_id("")
		self.socket_context_id = self.SocketStatus.get_context_id("")
		self.user_context_id = self.UserStatus.get_context_id("")
		self.down_context_id = self.DownStatus.get_context_id("")
		self.up_context_id = self.UpStatus.get_context_id("")

		self.MainWindow.connect("delete-event", self.on_delete_event)
		self.MainWindow.connect('window-state-event', self.window_state_event_cb)
		self.MainWindow.connect("destroy", self.OnDestroy)
		self.MainWindow.connect("key_press_event", self.OnKeyPress)
		self.MainWindow.connect("motion-notify-event", self.OnButtonPress)
		
		gobject.signal_new("network_event", gtk.Window, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
		gobject.signal_new("network_event_lo", gtk.Window, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
		self.MainWindow.connect("network_event", self.OnNetworkEvent)
		self.MainWindow.connect("network_event_lo", self.OnNetworkEvent)

		if sys.platform.startswith("win"):
			self.now_playing1.set_sensitive(False)
		

		
		for thing in config["interests"]["likes"]:
			self.likes[thing] = self.likeslist.append([thing])
		for thing in config["interests"]["dislikes"]:
			self.dislikes[thing] = self.dislikeslist.append([thing])

		for w in self.ChatNotebook, self.PrivatechatNotebook, self.UserInfoNotebook, self.UserBrowseNotebook, self.SearchNotebook:
			w.set_tab_closers(config["ui"]["tabclosers"])
			w.show_images(config["ui"]["tab_icons"])
			
		for label_tab in [self.ChatTabLabel, self.PrivateChatTabLabel, self.SearchTabLabel, self.UserInfoTabLabel, self.DownloadsTabLabel, self.UploadsTabLabel, self.UserBrowseTabLabel, self.InterestsTabLabel]:
			label_tab.show_image(config["ui"]["tab_icons"])
			label_tab.set_angle(config["ui"]["labelmain"])
			
		self.translux = None
		self.TransparentTint()
		self.LogScrolledWindow = gtk.ScrolledWindow()
		self.LogScrolledWindow.set_shadow_type(gtk.SHADOW_IN)
		self.LogScrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.LogScrolledWindow.show()

		self.LogWindow = gtk.TextView()
		self.LogWindow.set_wrap_mode(gtk.WRAP_WORD)
		self.LogWindow.set_cursor_visible(False)
		self.LogWindow.set_editable(False)
		
		self.LogScrolledWindow.add(self.LogWindow)
		self.LogWindow.connect("button-press-event", self.OnPopupLogMenu)
		
		

		if self.translux:
			self.LogScrolledWindow.get_vadjustment().connect("value-changed", lambda *args: self.LogWindow.queue_draw())
			self.translux.subscribe(self.LogWindow, lambda: self.LogWindow.get_window(gtk.TEXT_WINDOW_TEXT))
	        
		if config["logging"]["logcollapsed"]:
			self.hide_log_window1.set_active(1)
		else:
			self.vpaned1.pack2(self.LogScrolledWindow, False, True)
			self.hide_log_window1.set_active(0)
		
		if config["ui"]["roomlistcollapsed"]:
			self.hide_room_list1.set_active(1)
		else:
			self.vpaned3.pack2(self.roomlist.vbox2,True, True)
			self.hide_room_list1.set_active(0)
		self.LogWindow.show()

		self.userlistvbox = gtk.VBox(False, 0)
		self.userlistvbox.show()
		self.userlistvbox.set_spacing(3)
		self.userlistvbox.set_border_width(0)
		
		self.BuddiesLabel = gtk.Label()
		self.BuddiesLabel.set_markup("<b>"+_("Buddies")+"</b>")
		self.BuddiesLabel.set_padding(0, 0)
		
		self.userlistvbox.pack_start(self.BuddiesLabel, False, False)
		
		self.userlistSW = gtk.ScrolledWindow()
		self.userlistSW.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.userlistSW.show()
		self.userlistSW.set_shadow_type(gtk.SHADOW_NONE)

		self.UserList = gtk.TreeView()
		self.UserList.show()
		self.UserList.set_headers_visible(True)
		self.userlistSW.add(self.UserList)
	
		self.userlistvbox.pack_start(self.userlistSW, True, True, 0)
	
		self.UserHbox = gtk.HBox(False, 3)
		self.UserHbox.set_border_width(0)
		self.UserHbox.show()
	
	
		self.label12 = gtk.Label(_("Add Buddy: "))
		self.label12.set_padding(0, 0)
		self.label12.show()
		self.UserHbox.pack_start(self.label12, False, False)
	
		self.AddUserEntry = gtk.Entry()
		self.AddUserEntry.set_text("")
		self.AddUserEntry.set_editable(True)
		self.AddUserEntry.show()
		self.AddUserEntry.set_visibility(True)
		self.AddUserEntry.connect("activate", self.OnAddUser)
		self.UserHbox.pack_start(self.AddUserEntry, True, True)

		self.MoveList = gtk.ToggleButton()
		self.MoveList.show()
		self.MoveListAlignment = gtk.Alignment(0.5, 0.5, 0, 0)
		self.MoveListAlignment.show()

		self.MoveListImage = gtk.Image()
		self.MoveListImage.set_from_stock(gtk.STOCK_JUMP_TO, 1)
		self.MoveListImage.show()

	
		self.MoveListAlignment.add(self.MoveListImage)

		self.MoveList.add(self.MoveListAlignment)
		
		

		self.UserHbox.pack_end(self.MoveList, False, True)
		self.MoveList.connect("toggled", self.OnMoveList)
		
		self.userlistvbox.pack_start(self.UserHbox, False, True)

		if int(config["ui"]["buddylistinchatrooms"]):
			self.buddylist_in_chatrooms1.set_active(1)
			self.BuddiesLabel.show()
		else:

			self.BuddiesTabLabel = ImageLabel(_("Buddy list"), self.images["empty"])
			self.BuddiesTabLabel.set_text_color(0)
			self.BuddiesTabLabel.show()
			self.BuddiesLabel.hide()
			self.MainNotebook.append_page(self.userlistvbox, self.BuddiesTabLabel)
		
		
		for l in [self.ChatTabLabel, self.PrivateChatTabLabel, self.DownloadsTabLabel, self.UploadsTabLabel, self.SearchTabLabel, self.UserInfoTabLabel, self.UserBrowseTabLabel, self.InterestsTabLabel]:
			l.set_text_color(0)
		
		if config["ticker"]["hide"]:
			self.hide_tickers1.set_active(1)
		self.UpdateColours(1)
		self.settingswindow = SettingsWindow(self)
		self.settingswindow.SettingsWindow.connect("settings-closed", self.OnSettingsClosed)

		self.chatrooms = self.ChatNotebook
		self.Searches = self.SearchNotebook
		self.downloads = Downloads(self)
		self.uploads = Uploads(self)
		self.userlist = UserList(self)

		self.privatechats = self.PrivatechatNotebook
		self.userinfo = self.UserInfoNotebook
		self.userbrowse = self.UserBrowseNotebook

		self.userinfo.SetTabLabel(self.UserInfoTabLabel)
		self.userbrowse.SetTabLabel(self.UserBrowseTabLabel)
		
		self.sUserinfoButton.connect("clicked", self.OnGetUserInfo)
		self.UserInfoCombo.child.connect("activate", self.OnGetUserInfo)
		
		self.sPrivateChatButton.connect("clicked", self.OnGetPrivateChat)
		self.UserPrivateCombo.child.connect("activate", self.OnGetPrivateChat)
		
		self.sSharesButton.connect("clicked", self.OnGetShares)
		self.UserBrowseCombo.child.connect("activate", self.OnGetShares)

		if config["columns"]["hideflags"]:
			self.HideFlags.set_active(1)
		else:
			self.HideFlags.set_active(0)
			
		self.SetUserStatus(_("Offline"))
		self.TrayApp = TrayApp(self)
		self.UpdateBandwidth()
		self.UpdateTransferButtons()
		# Search Methods
		self.searchroomslist = {}
		self.searchmethods = {}
		self.RoomSearchCombo.set_size_request(150, -1)
		self.UserSearchCombo.set_size_request(120, -1)
		self.UserSearchCombo.set_sensitive(False)
		thread.start_new_thread(self.BuddiesCombosFill, ("",))


		self.SearchMethod_List.clear()
		# Space after Joined Rooms is important, so it doesn't conflict
		# with any possible real room, but if it's not translated with the space
		# nothing awful will happen
		self.searchroomslist[_("Joined Rooms ")] = self.RoomSearchCombo_List.append([_("Joined Rooms ")])
		self.RoomSearchCombo.set_active_iter(self.searchroomslist[_("Joined Rooms ")])
		for method in [_("Global"), _("Buddies"), _("Rooms"), _("User")]:
			self.searchmethods[method] = self.SearchMethod_List.append([method])
		self.SearchMethod.set_active_iter(self.searchmethods[_("Global")])
		self.SearchMethod.connect("changed", self.OnSearchMethod)
		self.UserSearchCombo.hide()
		self.RoomSearchCombo.hide()
		###
		self.disconnect1.set_sensitive(0)
		self.awayreturn1.set_sensitive(0)
		self.check_privileges1.set_sensitive(0)

		self.gstreamer = gstreamer()


		if config["ui"]["chat_hidebuttons"]:
			self.HideChatButtons.set_active(1)
		else:
			self.HideChatButtons.set_active(0)

		if config["transfers"]["rescanonstartup"]:
			self.OnRescan()
		img = gtk.Image()
		img.set_from_pixbuf(self.images["away2"])
		self.awayreturn1.set_image(img)
		self.now = nowplaying.NowPlaying(self)
		self.SetTabPositions()

		ConfigUnset = self.np.config.needConfig()
		if ConfigUnset:
			if ConfigUnset > 1:
				self.connect1.set_sensitive(False)
				self.rescan1.set_sensitive(True)
					
				# Display Settings dialog
				self.OnSettings(None)
				
			else:
				
				# Connect anyway
				self.OnConnect(-1)
		else:
			self.OnConnect(-1)
		self.UpdateDownloadFilters()
		
		
		if use_trayicon and config["ui"]["trayicon"]:
			self.TrayApp.CREATE_TRAYICON = 1
			self.TrayApp.HAVE_TRAYICON = True
			self.TrayApp.Create()
		if trerror is not None and trerror != "":
			self.logMessage(trerror)
		self.SetAllToolTips()
	
	def on_delete_event(self, widget, event):
		if not self.np.config.sections["ui"]["exitdialog"]:
			return False
		if self.TrayApp.HAVE_TRAYICON and self.np.config.sections["ui"]["exitdialog"] == 2:
			if self.is_mapped:
				self.MainWindow.unmap()
				self.is_mapped = 0
			return True
		if self.TrayApp.HAVE_TRAYICON:
			option = QuitBox(self, title=_('Close Nicotine-Plus?'), message=_('Are you sure you wish to exit Nicotine-Plus at this time?'),tray=True, status="question", third=_("Send to tray") )
		else:
			option = QuitBox(self, title=_('Close Nicotine-Plus?'), message=_('Are you sure you wish to exit Nicotine-Plus at this time?'), tray=False, status="question" )
		
		return True
		
			
	def window_state_event_cb(self, window, event):
		if event.changed_mask and gtk.gdk.WINDOW_STATE_ICONIFIED:
			if event.new_window_state and gtk.gdk.WINDOW_STATE_ICONIFIED:
				self.minimized = 1
			else:
				self.minimized = 0

	def NewNotification(self, message, title="Nicotine+"):
		if self.pynotify is None:
			return
		n = self.pynotify.Notification(title, message)
		n.set_icon_from_pixbuf(self.images["n"])
		try: n.attach_to_status_icon(self.TrayApp.trayicon_module)
		except:
			try: n.attach_to_widget(self.TrayApp.trayicon_module)
			except: pass
		try:
			n.show()
		except gobject.GError, error:
			self.logMessage(_("Notification Error: %s") % str(error))
				
	def OnMoveList(self, widget):
		self.buddylist_in_chatrooms1.set_active(not self.buddylist_in_chatrooms1.get_active())
		self.OnChatRooms(None)
		
	def LoadIcons(self):
		self.images = {}
		self.icons = {}
		self.flag_images = {}
		self.flag_users = {}

		for i in ["empty", "away", "online", "offline", "hilite", "hilite2", "connect", "disconnect", "away2", "n", "nicotinen"]:
			try:
				import imagedata
			except Exception, e:
				print e
			loader = gtk.gdk.PixbufLoader("png")
			if "icontheme" in self.np.config.sections["ui"]:
				path = os.path.expanduser(os.path.join(self.np.config.sections["ui"]["icontheme"], i +".png"))
				if os.path.exists(path):
					data = open(path, 'rb')
					s = data.read()
					loader.write(s, len(s))
					data.close()
					del s
				else:
					# default icons
					data = getattr(imagedata, i)
					loader.write(data, len(data))
			else:
				# default icons
				data = getattr(imagedata, i)
				loader.write(data, len(data))
			
			
			loader.close()
			self.images[i] = loader.get_pixbuf()

		
	def SaveColumns(self):
		for i in [self.userlist, self.chatrooms.roomsctrl, self.downloads, self.uploads, self.Searches]:
			i.saveColumns()
		self.np.config.writeConfig()
		
	def OnSearchMethod(self, widget):
		act = False
		if self.SearchMethod.get_active_text() == _("User"):
			self.UserSearchCombo.show()
			act = True
		else:
			self.UserSearchCombo.hide()
		self.UserSearchCombo.set_sensitive(act)
		act = False
		if self.SearchMethod.get_active_text() == _("Rooms"):
			act = True
			self.RoomSearchCombo.show()
		else:
			self.RoomSearchCombo.hide()
		self.RoomSearchCombo.set_sensitive(act)
		
	def CreateRecommendationsWidgets(self):
		self.likes = {}
		self.likeslist = gtk.ListStore(gobject.TYPE_STRING)
		self.likeslist.set_sort_column_id(0, gtk.SORT_ASCENDING)
		cols = utils.InitialiseColumns(self.LikesList, [_("I like")+":", 0, "text", self.CellDataFunc])
		cols[0].set_sort_column_id(0)
		self.LikesList.set_model(self.likeslist)
		self.RecommendationsList.set_property("rules-hint", True)
		self.RecommendationUsersList.set_property("rules-hint", True)
		self.til_popup_menu = popup = utils.PopupMenu(self)
		popup.setup(
			("#" + _("_Remove this item"), self.OnRemoveThingILike, gtk.STOCK_CANCEL),
			("#" + _("Re_commendations for this item"), self.OnRecommendItem, gtk.STOCK_INDEX),
			("", None),
			("#" + _("_Search for this item"), self.OnRecommendSearch, gtk.STOCK_FIND),
		)
		self.LikesList.connect("button_press_event", self.OnPopupTILMenu)

		self.dislikes = {}
		self.dislikeslist = gtk.ListStore(gobject.TYPE_STRING)
		self.dislikeslist.set_sort_column_id(0, gtk.SORT_ASCENDING)
		cols = utils.InitialiseColumns(self.DislikesList, [_("I dislike")+":", 0, "text", self.CellDataFunc])
		cols[0].set_sort_column_id(0)
		self.DislikesList.set_model(self.dislikeslist)
		self.tidl_popup_menu = popup = utils.PopupMenu(self)
		popup.setup(("#" + _("_Remove this item"), self.OnRemoveThingIDislike, gtk.STOCK_CANCEL),
		("", None),
			("#" + _("_Search for this item"), self.OnRecommendSearch, gtk.STOCK_FIND),)
		self.DislikesList.connect("button_press_event", self.OnPopupTIDLMenu)

		cols = utils.InitialiseColumns(self.RecommendationsList,
			[_("Item"), 0, "text", self.CellDataFunc],
			[_("Rating"), 75, "text", self.CellDataFunc])
		cols[0].set_sort_column_id(0)
		cols[1].set_sort_column_id(2)
		self.recommendationslist = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT)
		self.RecommendationsList.set_model(self.recommendationslist)
		self.r_popup_menu = popup = utils.PopupMenu(self)
		popup.setup(
			("$" + _("I _like this"), self.OnLikeRecommendation),
			("$" + _("I _don't like this"), self.OnDislikeRecommendation),
			("#" + _("_Recommendations for this item"), self.OnRecommendRecommendation, gtk.STOCK_INDEX),
			("", None),
			("#" + _("_Search for this item"), self.OnRecommendSearch, gtk.STOCK_FIND),
		)
		self.RecommendationsList.connect("button_press_event", self.OnPopupRMenu)
		cols = utils.InitialiseColumns(self.UnrecommendationsList,
			[_("Item"), 0, "text", self.CellDataFunc],
			[_("Rating"), 75, "text", self.CellDataFunc])
		cols[0].set_sort_column_id(0)
		cols[1].set_sort_column_id(2)
		self.unrecommendationslist = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT)
		self.UnrecommendationsList.set_model(self.unrecommendationslist)
		self.ur_popup_menu = popup = utils.PopupMenu(self)
		popup.setup(
			("$" + _("I _like this"), self.OnLikeRecommendation),
			("$" + _("I _don't like this"), self.OnDislikeRecommendation),
			("#" + _("_Recommendations for this item"), self.OnRecommendRecommendation, gtk.STOCK_INDEX),
			("", None),
			("#" + _("_Search for this item"), self.OnRecommendSearch, gtk.STOCK_FIND),
		)
		self.UnrecommendationsList.connect("button_press_event", self.OnPopupUnRecMenu)
		self.RecommendationsExpander.connect("activate", self.RecommendationsExpanderStatus)
		self.UnrecommendationsExpander.connect("activate", self.RecommendationsExpanderStatus)

		cols = utils.InitialiseColumns(self.RecommendationUsersList, 
			["", 20, "pixbuf"],
			[_("User"), 100, "text", self.CellDataFunc],
			[_("Speed"), 0, "text", self.CellDataFunc],
			[_("Files"), 0, "text", self.CellDataFunc],
		)
		cols[0].set_sort_column_id(4)
		cols[1].set_sort_column_id(1)
		cols[2].set_sort_column_id(5)
		cols[3].set_sort_column_id(6)
		self.recommendationusers = {}
		self.recommendationuserslist = gtk.ListStore(gtk.gdk.Pixbuf, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT, gobject.TYPE_INT, gobject.TYPE_INT)
		self.RecommendationUsersList.set_model(self.recommendationuserslist)
		self.recommendationuserslist.set_sort_column_id(1, gtk.SORT_ASCENDING)
		self.ru_popup_menu = popup = utils.PopupMenu(self)
		popup.setup(
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
		)
		self.RecommendationUsersList.connect("button_press_event", self.OnPopupRUMenu)
		
	def Notification(self, location, user, room=None):
		hilites = self.TrayApp.tray_status["hilites"]
		if location == "rooms" and room != None and user != None:
			if room not in hilites["rooms"]:
				hilites["rooms"].append(room)
				self.sound("room_nick", user, place=room)
				self.TrayApp.SetImage()
				#self.MainWindow.set_urgency_hint(True)
		elif location == "private":
			if user in hilites[location]:
				hilites[location].remove(user)
				hilites[location].append(user)
			if user not in hilites[location]: 
				hilites[location].append(user)
				self.sound(location, user)
				self.TrayApp.SetImage()
				#self.MainWindow.set_urgency_hint(True)
		self.TitleNotification(user)
		
	def ClearNotification(self, location, user, room=None):
		if location == "rooms" and room != None:
			if room in self.TrayApp.tray_status["hilites"]["rooms"]:
				self.TrayApp.tray_status["hilites"]["rooms"].remove(room)
		elif location == "private":	
			if user in self.TrayApp.tray_status["hilites"]["private"]: 
				self.TrayApp.tray_status["hilites"]["private"].remove(user)
		self.TitleNotification(user)
		self.TrayApp.SetImage()
		
	def TitleNotification(self, user=None):
		if self.TrayApp.tray_status["hilites"]["rooms"] == [] and self.TrayApp.tray_status["hilites"]["private"] == []:
			# Reset Title
			if self.MainWindow.get_title() != _("Nicotine+") + " " + version:  
				self.MainWindow.set_title(_("Nicotine+") + " " + version)
		else:
			# Private Chats have a higher priority
			if len(self.TrayApp.tray_status["hilites"]["private"]) > 0:
				user = self.TrayApp.tray_status["hilites"]["private"][-1]
				self.MainWindow.set_title(_("Nicotine+") + " " + version+ " :: " +  _("Private Message from %(user)s" % {'user':user} ) )
			# Allow for the possibility the username is not available
			elif len(self.TrayApp.tray_status["hilites"]["rooms"]) > 0:
				room = self.TrayApp.tray_status["hilites"]["rooms"][-1]
				if user == None:
					self.MainWindow.set_title(_("Nicotine+") + " " + version+ " :: " +  _("You've been mentioned in the %(room)s room" % {'room':room} ) )
				else:
					self.MainWindow.set_title(_("Nicotine+") + " " + version+ " :: " +  _("%(user)s mentioned you in the %(room)s room" % {'user':user, 'room':room } ) )
					
	def new_tts(self, message):
		if not self.np.config.sections["ui"]["speechenabled"]:
			return
		if message not in self.tts:
			self.tts.append(message)
			thread.start_new_thread(self.play_tts, ())
			
	def play_tts(self):
		if self.tts_playing:
			self.continue_playing = True
			return
		for message in self.tts[:]:
			self.tts_player(message)
			if message in self.tts:
				self.tts.remove(message)
		self.tts_playing = False
		if self.continue_playing:
			self.continue_playing = False
			self.play_tts()
			
	def tts_clean(self, message):
		for i in ["_", "[", "]", "(", ")"]:
			message = message.replace(i, " ")
		return message
		
	def tts_player(self, message):
		self.tts_playing = True
		os.system(self.np.config.sections["ui"]["speechcommand"]  % message)

		
	def sound(self, message, user, place=None):
		if sys.platform == "win32":
			return
		
		if self.np.config.sections["ui"]["speechenabled"]:
			if message == "room_nick" and place is not None:
				self.new_tts(_("%(myusername)s, the user, %(username)s has mentioned your name in the room, %(place)s.") %{ "myusername": self.np.config.sections[ "server"]["login"], "username": user, "place": place} )
			elif message == "private":
				self.new_tts("%(myusername)s, you have recieved a private message from %(username)s." % {"myusername":self.np.config.sections["server"]["login"], "username":user } )
			return
		if "soundenabled" not in self.np.config.sections["ui"] or not self.np.config.sections["ui"]["soundenabled"]:
			return
		if "soundcommand" not in self.np.config.sections["ui"]:
			return
		command = self.np.config.sections["ui"]["soundcommand"]
		path = None
		exists = 0
		if message == "private":
			soundtitle = "private"
		elif message == "room_nick":
			soundtitle = "room_nick"
			
		if "soundtheme" in self.np.config.sections["ui"]:
			path = os.path.expanduser(os.path.join(self.np.config.sections["ui"]["soundtheme"], "%s.ogg" % soundtitle))
			if os.path.exists(path): exists = 1
			else: path = None	
		if not exists:
			path = "%s/share/nicotine/sounds/default/%s.ogg" %(sys.prefix, soundtitle)
			if os.path.exists(path): exists = 1
			else: path = None
		if not exists:
			path = "sounds/default/%s.ogg" % soundtitle
			if os.path.exists(path): exists = 1
			else: path = None
		if path != None and exists:
			if command == "Gstreamer (gst-python)":
				if self.gstreamer.player is None:
					return
				self.gstreamer.play(path)
			else:
				os.system("%s %s &" % ( command, path))

	
			
	def download_large_folder(self, username, folder, files, numfiles, msg):
		FolderDownload(self, title=_('Nicotine+')+': Download %(num)i files?' %{'num':numfiles}, message=_("Are you sure you wish to download %(num)i files from %(user)s's directory %(folder)s?") %{'num': numfiles, 'user':username, 'folder':folder } , modal=True, data=msg, callback=self.folder_download_response )
		
	def folder_download_response(self, dialog, response, data): 

		if response == gtk.RESPONSE_CANCEL:
			dialog.destroy()
			return
		elif response == gtk.RESPONSE_OK:
			dialog.destroy()
			self.np.transfers.FolderContentsResponse(data)
			
	def on_quit_response(self, dialog, response): 
		dialog.destroy()
		
			
		if response == gtk.RESPONSE_OK:
			if sys.platform == "win32" and self.TrayApp.trayicon:
				self.TrayApp.trayicon.hide_icon()
			self.MainWindow.destroy()
			gtk.main_quit()
			
		elif response == gtk.RESPONSE_CANCEL:
			pass
			
		elif response == gtk.RESPONSE_REJECT:
			
			if self.is_mapped:
				self.MainWindow.unmap()
				self.is_mapped = 0

	def on_clear_response(self, dialog, response, direction):
		dialog.destroy()
		
		if response == gtk.RESPONSE_OK:
			if direction == "down":
				self.downloads.ClearTransfers(["Queued"])
			elif direction == "up":
				self.uploads.ClearTransfers(["Queued"])
				
	def onOpenRoomList(self, dialog, response):
		dialog.destroy()
		if response == gtk.RESPONSE_OK:
			self.hide_room_list1.set_active(0)
	
			
	def OnGetUserInfo(self, widget):
		text = self.UserInfoCombo.child.get_text()
		if not text:
			return
		self.LocalUserInfoRequest(text)
		self.UserInfoCombo.child.set_text("")
		
	def OnGetShares(self, widget):
		text = self.UserBrowseCombo.child.get_text()
		if not text:
			return
		self.BrowseUser(text)
		self.UserBrowseCombo.child.set_text("")
	
	def OnLoadFromDisk(self, widget):
		configdir, config = os.path.split(self.np.config.filename)
		sharesdir = os.path.abspath(configdir+os.sep+"usershares"+os.sep)
		try:
			if not os.path.exists(sharesdir):
				os.mkdir(sharesdir)
		except Exception, msg:
			error = _("Can't create directory '%(folder)s', reported error: %(error)s" % {'folder':sharesdir, 'error':msg})
			print error
			self.logMessage(error)
		shares = ChooseFile(self.MainWindow.get_toplevel(), sharesdir)
		if shares is None:
			return
		for share in shares: # iterate over selected files
			share1 = share
			break
		try:
			
			import pickle, bz2
			sharefile = bz2.BZ2File(share1)
			list1 = pickle.load(sharefile)
			sharefile.close()
			if not isinstance(list1, dict):
				raise TypeError, "Bad data in file %(sharesdb)s" % {'sharesdb':share1}
			username = share1.split(os.sep)[-1]
			self.userbrowse.InitWindow(username, None)
			if username in self.userbrowse.users:
				self.userbrowse.users[username].LoadShares(list1)
		except Exception, msg:
			error = _("Loading Shares from disk failed: %(error)s" % {'error':msg})
			self.logMessage(error)
			print error
			
	def OnNowPlayingConfigure(self, widget):
		
		self.now.NowPlaying.show()
		self.now.NowPlaying.deiconify()
		
		
		
	def OnGetPrivateChat(self, widget):
		text = self.UserPrivateCombo.child.get_text()
		if not text:
			return
		self.privatechats.SendMessage(text, None, 1)
		self.UserPrivateCombo.child.set_text("")
		
	def OnOpenPrivateChat(self, widget, prefix = ""):
		# popup
		users = []
		for entry in self.np.config.sections["server"]["userlist"]:
			users.append(entry[0])
		users.sort()
		user = input_box(self, title=_('Nicotine+:')+" "+_("Start Message"),
		message=_('Enter the User who you wish to send a private message:'),
		default_text='', droplist=users)
		if user is not None:
			self.privatechats.SendMessage(user, None, 1)
			self.MainNotebook.set_current_page(1)
			
	def OnGetAUsersInfo(self, widget, prefix = ""):
		# popup
		users = []
		for entry in self.np.config.sections["server"]["userlist"]:
			users.append(entry[0])
		users.sort()
		user = input_box(self, title=_('Nicotine+: Get User Info'),
		message=_('Enter the User whose User Info you wish to recieve:'),
		default_text='', droplist=users)
		if user is None:
			pass
		else:
			self.LocalUserInfoRequest(user)
			
	def OnGetAUsersIP(self, widget, prefix = ""):
		users = []
		for entry in self.np.config.sections["server"]["userlist"]:
			users.append(entry[0])
		users.sort()
		user = input_box(self, title=_("Nicotine+: Get A User's IP"),
		message=_('Enter the User whose IP Address you wish to recieve:'),
		default_text='', droplist=users)
		if user is None:
			pass
		else:
			self.np.queue.put(slskmessages.GetPeerAddress(user))

			
	def OnGetAUsersShares(self, widget, prefix = ""):
		users = []
		for entry in self.np.config.sections["server"]["userlist"]:
			users.append(entry[0])
		users.sort()
		user = input_box(self, title=_("Nicotine+: Get A User's Shares List"),
		message=_('Enter the User whose Shares List you wish to recieve:'),
		default_text='', droplist=users)
		if user is None:
			pass
		else:
			self.BrowseUser(user)
			

	def button_press(self, widget, event):
		try:

			if event.type == gtk.gdk.BUTTON_PRESS:
				widget.popup(None, None, None, event.button, event.time)
				
				# Tell calling code that we have handled this event the buck
				# stops here.
				return True
				# Tell calling code that we have not handled this event pass it on.
			return False
		except Exception,e:
			print "button_press error", e


				
	def get_custom_widget(self, id, string1, string2, int1, int2):
		ui = self.np.config.sections["ui"]
		if id == "ChatNotebook":
			return ChatRooms(self)
		elif id == "SearchNotebook":
			return Searches(self)
		#IconNotebook(self.images, ui["labelsearch"], ui["tabclosers"])
		elif id == "PrivatechatNotebook":
			return PrivateChats(self)
		elif id == "UserInfoNotebook":
			notebook = UserTabs(self, UserInfo)
			return notebook
		elif id == "UserBrowseNotebook":
			notebook = UserTabs(self, UserBrowse)
			return notebook
		elif id in ("UserSearchCombo", "UserPrivateCombo", "UserInfoCombo", "UserBrowseCombo"):
			comboentry = BuddiesComboBoxEntry(self)
			self.BuddiesComboEntries.append(comboentry)
			return comboentry
		elif string1 == "ImageLabel":
			return ImageLabel(string2, self.images["empty"])
		else:
			return MainWindow.get_custom_widget(self, id, string1, string2, int1, int2)
		
	def BuddiesCombosFill(self, nothing):
		
		for widget in self.BuddiesComboEntries:
			gobject.idle_add(widget.Fill)
			
	def getTabPosition(self, string):
		if string == "top":
			position = gtk.POS_TOP
		elif string == "bottom":
			position = gtk.POS_BOTTOM
		elif string == "left":
			position = gtk.POS_LEFT
		elif string == "right":
			position = gtk.POS_RIGHT
		else:
			position = gtk.POS_TOP
		return position
		
	def OnAutoAway(self):
		if not self.away:
			self.autoaway = True
			self.OnAway(None)
		return False
	
	def OnButtonPress(self, widget, event):
		if self.autoaway:
			self.OnAway(None)
			self.autoaway = False
		if self.awaytimer is not None:
			gobject.source_remove(self.awaytimer)
			autoaway = self.np.config.sections["server"]["autoaway"]
			if autoaway > 0:
				self.awaytimer = gobject.timeout_add(1000*60*autoaway, self.OnAutoAway)
			else:
				self.awaytimer = None
			
	def OnKeyPress(self, widget, event):
		self.OnButtonPress(None, None)
		if event.state & (gtk.gdk.MOD1_MASK|gtk.gdk.CONTROL_MASK) != gtk.gdk.MOD1_MASK:
			return False
		for i in range(1, 10):
			if event.keyval == gtk.gdk.keyval_from_name(str(i)):
				self.MainNotebook.set_current_page(i-1)
				widget.emit_stop_by_name("key_press_event")
				return True
		return False
		
	def emit_network_event(self, msgs):
		lo = [msg for msg in msgs if msg.__class__ is slskmessages.FileSearchResult]
		hi = [msg for msg in msgs if msg.__class__ is not slskmessages.FileSearchResult]
		if hi:
			self.MainWindow.emit("network_event", hi)
		if lo:
			self.MainWindow.emit("network_event_lo", lo)
		return False
	
        ## Recieved a network event via emit_network_event 
        ## with at least one, but possibly more messages
        ## call the appropriate event class for these message
        # @param self NicotineFrame (Class)
        # @param widget the main window
        # @param msgs a list of messages 
	def OnNetworkEvent(self, widget, msgs):
		for i in msgs:
			if i.__class__ in self.np.events:
				self.np.events[i.__class__](i)
			else:
				self.logMessage("No handler for class %s %s" % (i.__class__, vars(i)))

	def callback(self, msgs):
		gtk.gdk.threads_enter()
		if len(msgs) > 0:
			gobject.idle_add(self.emit_network_event, msgs[:])
		gtk.gdk.threads_leave()

	def networkcallback(self,msgs):
		gtk.gdk.threads_enter()
		curtime = time.time()
		for i in msgs[:]:
			if i.__class__ is slskmessages.DownloadFile or i.__class__ is slskmessages.UploadFile:
				self.transfermsgs[i.conn] = i
				msgs.remove(i)
			if i.__class__ is slskmessages.ConnClose:
				msgs = self.postTransferMsgs(msgs,curtime)
		if curtime-self.transfermsgspostedtime > 1.0:
			msgs = self.postTransferMsgs(msgs,curtime)
		if len(msgs) > 0:
			gobject.idle_add(self.emit_network_event, msgs[:])
		gtk.gdk.threads_leave()

	def postTransferMsgs(self,msgs,curtime):
		trmsgs = []
		for i in self.transfermsgs.keys():
			trmsgs.append(self.transfermsgs[i])
		msgs = trmsgs+msgs
		self.transfermsgs = {}
		self.transfermsgspostedtime = curtime
		return msgs
	
	def CellDataFunc(self, column, cellrenderer, model, iter):
		colour = self.np.config.sections["ui"]["search"]
		if colour == "":
			colour = None
		cellrenderer.set_property("foreground", colour)
		
	def changecolour(self, tag, colour):
		if colour in self.frame.np.config.sections["ui"]:
			color = self.frame.np.config.sections["ui"][colour]
		else:
			color = None
		font = self.frame.np.config.sections["ui"]["chatfont"]
		
		if color:
			if color == "":
				color = None
			tag.set_property("foreground", color)
			tag.set_property("font", font)
		
		else:
			tag.set_property("font", font)
			
	def UpdateColours(self, first=0):
		color = self.np.config.sections["ui"]["chatremote"]
		font = self.np.config.sections["ui"]["chatfont"]

		if color == "":
			map = self.LogWindow.get_style().copy()
			colour = map.text[gtk.STATE_NORMAL]
		else:
			colour = gtk.gdk.color_parse(color)
		if font == "":
			font = None
		if first:
			self.tag_log = self.LogWindow.get_buffer().create_tag()
		self.tag_log.set_property("font", font)
		self.tag_log.set_property("foreground-gdk", colour)

		
		self.SetTextBG(self.LogWindow)
		self.SetTextBG(self.UserList)
		self.SetTextBG(self.RecommendationsList)
		self.SetTextBG(self.UnrecommendationsList)
		self.SetTextBG(self.RecommendationUsersList)
		self.SetTextBG(self.LikesList)
		self.SetTextBG(self.DislikesList)
		self.SetTextBG(self.UserPrivateCombo.child)
		self.SetTextBG(self.UserInfoCombo.child)
		self.SetTextBG(self.UserBrowseCombo.child)
		self.SetTextBG(self.AddUserEntry)
		self.SetTextBG(self.SearchEntry)
		
		
		
	def SetTextBG(self, widget, bgcolor="", fgcolor=""):
		if bgcolor == "" and self.np.config.sections["ui"]["textbg"] == "":
			colour = None
		else:
			if bgcolor == "":
				bgcolor = self.np.config.sections["ui"]["textbg"]
			colour = gtk.gdk.color_parse(bgcolor)
			
		widget.modify_base(gtk.STATE_NORMAL, colour)
		widget.modify_bg(gtk.STATE_NORMAL, colour)
		widgetlist = [gtk.Entry, gtk.SpinButton]
		if SEXY:
			widgetlist.append(sexy.SpellEntry)
		if type(widget) in widgetlist:
			if fgcolor != "":
				colour = gtk.gdk.color_parse(fgcolor)
			elif fgcolor == "" and self.np.config.sections["ui"]["inputcolor"] == "":
				colour = None
			elif fgcolor == "" and self.np.config.sections["ui"]["inputcolor"] != "":
				fgcolor = self.np.config.sections["ui"]["inputcolor"]
				colour = gtk.gdk.color_parse(fgcolor)
				
			widget.modify_text(gtk.STATE_NORMAL, colour)
			widget.modify_fg(gtk.STATE_NORMAL, colour)
			
	def logMessage(self, msg, debug = None):
		if "LogWindow" not in self.__dict__:
			self.log_queue.append((msg, debug))
			return False
		for message in self.log_queue[:]:
			old_msg, old_debug = message
			if old_debug is None or self.showdebug:
				AppendLine(self.LogWindow, old_msg, self.tag_log)
				if self.np.config.sections["logging"]["logcollapsed"]:
					self.SetStatusText(old_msg)
			self.log_queue.remove(message)
		if debug is None or self.showdebug:

			AppendLine(self.LogWindow, msg, self.tag_log)
			if self.np.config.sections["logging"]["logcollapsed"]:
				self.SetStatusText(msg)
		return False
			
	def ScrollBottom(self, widget):
		va = widget.get_vadjustment()
		va.set_value(va.upper - va.page_size)
		widget.set_vadjustment(va)
		return False
	
	def SetStatusText(self, msg):
		self.Statusbar.pop(self.status_context_id)
		self.Statusbar.push(self.status_context_id, msg)
		
	def OnWindowChange(self, widget, blag):
		(width, height)= self.MainWindow.get_size()
		self.np.config.sections["ui"]["height"] = height
		self.np.config.sections["ui"]["width"] = width
		
	def OnDestroy(self, widget):
		if self.np.servertimer is not None:
			self.np.servertimer.cancel()
		if self.np.searchResultsTimer is not None:
			self.np.searchResultsTimer.cancel()
		if self.np.respondDistributedTimer is not None:
			self.np.respondDistributedTimer.cancel()
		self.np.StopTimers()
		if self.np.transfers is not None:
			self.np.transfers.AbortTransfers()
			if self.np.transfers.uploadQueueTimer is not None:
				self.np.transfers.uploadQueueTimer.cancel()
		
		self.np.config.sections["privatechat"]["users"] = list(self.privatechats.users.keys())
		if not self.manualdisconnect:
			self.OnDisconnect(None)
		self.np.config.writeConfig()
		self.np.protothread.abort()
		if sys.platform == "win32":
			if self.TrayApp.trayicon:
				self.TrayApp.trayicon.hide_icon()
		gtk.main_quit()
		
	def OnConnect(self, widget):
		self.TrayApp.tray_status["status"] = "connect"
		self.TrayApp.SetImage()
		if self.np.serverconn is not None:
			return
		if widget != -1:
			while not self.np.queue.empty():
				self.np.queue.get(0)
		self.SetUserStatus("...")
		server = self.np.config.sections["server"]["server"]
		self.SetStatusText(_("Connecting to %(host)s:%(port)s") %{'host':server[0],'port':server[1]} )
		self.np.queue.put(slskmessages.ServerConn(None, server))
		if self.np.servertimer is not None:
			self.np.servertimer.cancel()
			self.np.servertimer = None

	def OnDisconnect(self, event):
		self.disconnect1.set_sensitive(0)
		
		self.manualdisconnect = 1
		self.np.queue.put(slskmessages.ConnClose(self.np.serverconn))

	def FetchUserListStatus(self):
		for user in self.userlist.userlist:
			self.np.queue.put(slskmessages.AddUser(user[0]))

		return False
		
	def ConnClose(self, conn, addr):
		if self.awaytimer is not None:
			gobject.source_remove(self.awaytimer)
			self.awaytimer = None
		if self.autoaway:
			self.autoaway = self.away = False
		self.SetWidgetOnlineStatus(False)

		
		self.SetUserStatus(_("Offline"))
		self.TrayApp.tray_status["status"] = "disconnect"
		self.TrayApp.SetImage()
		self.Searches.interval = 0
		self.chatrooms.ConnClose()
		self.privatechats.ConnClose()
		self.Searches.ConnClose()
		self.uploads.ConnClose()
		self.downloads.ConnClose()
		self.userlist.ConnClose()
		self.userinfo.ConnClose()
		self.userbrowse.ConnClose()
		
	def SetWidgetOnlineStatus(self, status):
		self.connect1.set_sensitive(not status)
		self.disconnect1.set_sensitive(status)
		self.awayreturn1.set_sensitive(status)
		self.check_privileges1.set_sensitive(status)

		self.roomlist.CreateRoomEntry.set_sensitive(status)
		self.roomlist.RoomsList.set_sensitive(status)
		self.UserPrivateCombo.set_sensitive(status)
		self.sPrivateChatButton.set_sensitive(status)
		self.UserBrowseCombo.set_sensitive(status)
		self.sSharesButton.set_sensitive(status)
		self.UserInfoCombo.set_sensitive(status)
		self.sUserinfoButton.set_sensitive(status)
		
		self.UserSearchCombo.set_sensitive(status)
		self.SearchEntryCombo.set_sensitive(status)
		
		self.SearchButton.set_sensitive(status)
		self.SimilarUsersButton.set_sensitive(status)
		self.GlobalRecommendationsButton.set_sensitive(status)
		self.RecommendationsButton.set_sensitive(status)

		self.DownloadButtons.set_sensitive(status)
		self.UploadButtons.set_sensitive(status)
		
	def ConnectError(self, conn):
		self.SetWidgetOnlineStatus(False)
		
		self.SetUserStatus(_("Offline"))
		self.TrayApp.tray_status["status"] = "disconnect"
		self.TrayApp.SetImage()
		self.uploads.ConnClose()
		self.downloads.ConnClose()
		
	def SetUserStatus(self, status):
		self.UserStatus.pop(self.user_context_id)
		self.UserStatus.push(self.user_context_id, status)
		
	def SetSocketStatus(self, status):
		self.SocketStatus.pop(self.socket_context_id)
		self.SocketStatus.push(self.socket_context_id, _("%s Connections") % status)
		
	def InitInterface(self, msg):
		if self.away == 0:
			self.SetUserStatus(_("Online"))
			self.TrayApp.tray_status["status"] = "connect"
			self.TrayApp.SetImage()
			autoaway = self.np.config.sections["server"]["autoaway"]
			if autoaway > 0:
				self.awaytimer = gobject.timeout_add(1000*60*autoaway, self.OnAutoAway)
			else:
				self.awaytimer = None
		else:
			self.SetUserStatus(_("Away"))
			self.TrayApp.tray_status["status"] = "away2"
			self.TrayApp.SetImage()

		self.SetWidgetOnlineStatus(True)

		self.uploads.InitInterface(self.np.transfers.uploads)
		self.downloads.InitInterface(self.np.transfers.downloads)
		gobject.idle_add(self.FetchUserListStatus)
		
		AppendLine(self.LogWindow, self.np.decode(msg.banner), self.tag_log)
		return self.privatechats, self.chatrooms, self.userinfo, self.userbrowse, self.Searches, self.downloads, self.uploads, self.userlist

	def GetStatusImage(self, status):
		if status == 1:
			return self.images["away"]
		elif status == 2:
			return self.images["online"]
		else:
			return self.images["offline"]
		
	def HasUserFlag(self, user, flag):
		if flag not in self.flag_images:
			self.GetFlagImage(flag)
		if flag not in self.flag_images:
			return
		self.flag_users[user] = flag
		self.chatrooms.roomsctrl.SetUserFlag(user, flag)
		self.userlist.SetUserFlag(user, flag)
		
	def GetUserFlag(self, user):
		if user not in self.flag_users:
			for i in self.np.config.sections["server"]["userlist"]:
				if user == i[0] and i[6] is not None:
					return i[6]
			return None
		
		else:
			return self.flag_users[user]
		
	def GetFlagImage(self, flag):

		if flag is None: return
		if flag not in self.flag_images:
			if hasattr(imagedata, flag):
				loader = gtk.gdk.PixbufLoader("png")
				data = getattr(imagedata, flag)
				loader.write(data, len(data))
				loader.close()
				img = loader.get_pixbuf()
				self.flag_images[flag] = img
				return img
			else:
				return None
		else:
			return self.flag_images[flag]
	
	def OnShowDebug(self, widget):
		self.showdebug = widget.get_active()

	def OnAway(self, widget):
		self.away = (self.away+1) % 2
		if self.away == 0:
			self.SetUserStatus(_("Online"))
			self.TrayApp.tray_status["status"] = "connect"
			self.TrayApp.SetImage()
		else:
			self.SetUserStatus(_("Away"))
			self.TrayApp.tray_status["status"] = "away2"
			self.TrayApp.SetImage()
		self.np.queue.put(slskmessages.SetStatus(self.away and 1 or 2))
		self.privatechats.UpdateColours()

		
	def OnExit(self, widget):
		if sys.platform == "win32" and self.TrayApp.trayicon:
			self.TrayApp.trayicon.hide_icon()
		self.MainWindow.destroy()
	
	def OnSearch(self, widget):
		self.Searches.OnSearch()
		
	def OnClearSearchHistory(self, widget):
		self.Searches.OnClearSearchHistory()
		
	def ChatRequestIcon(self, status = 0):
		if status == 1 and not self.got_focus:
			self.MainWindow.set_icon(self.images["hilite2"])
		if self.MainNotebook.get_current_page() == 0:
			return
		if status == 0:
			if self.ChatTabLabel.get_image() == self.images["hilite"]:
				return
		self.ChatTabLabel.set_image(status == 1 and self.images["hilite"] or self.images["online"])
		self.ChatTabLabel.set_text_color(status+1)

	def RequestIcon(self, tablabel):
		if tablabel == self.PrivateChatTabLabel and not self.got_focus:
			self.MainWindow.set_icon(self.images["hilite2"])
		if self.current_tab != tablabel:
			tablabel.set_image(self.images["hilite"])
			tablabel.set_text_color(2)
			
		
	def OnSwitchPage(self, notebook, page, page_nr):
		tabLabels = [self.ChatTabLabel, self.PrivateChatTabLabel, self.DownloadsTabLabel, self.UploadsTabLabel, self.SearchTabLabel, self.UserInfoTabLabel, self.UserBrowseTabLabel, self.InterestsTabLabel]
		if "BuddiesTabLabel" in self.__dict__:
			tabLabels.append(self.BuddiesTabLabel)
		l = tabLabels[page_nr]
		n = [self.ChatNotebook, self.PrivatechatNotebook, None, None, self.SearchNotebook, self.UserInfoNotebook, self.UserBrowseNotebook, None, None][page_nr]
		self.current_tab = l
		if l is not None:
			l.set_image(self.images["empty"])
			l.set_text_color(0)
		if n is not None:
			n.popup_disable()
			n.popup_enable()
			if n.get_current_page() != -1:
				n.dismiss_icon(n, None, n.get_current_page())
				
		if page_nr == 0 and self.chatrooms:
			p = n.get_current_page()
			self.chatrooms.roomsctrl.OnSwitchPage(n, None, p, 1)
		elif page_nr == 1:
			p = n.get_current_page()
			self.privatechats.OnSwitchPage(n, None, p, 1)

	def UpdateBandwidth(self):
		def _calc(l):
			bandwidth = 0.0
			users = 0 
			l = [i for i in l if i.conn is not None]
			for i in l:
				if i.speed is not None:
					bandwidth = bandwidth + i.speed
			return len(l),bandwidth
		def _num_users(l):
			users = []
			
			for i in l:
				if i.user not in users:
					users.append(i.user)
			return len(users), len(l)
				
		if self.np.transfers is not None:
			usersdown, down = _calc(self.np.transfers.downloads)
			usersup, up = _calc(self.np.transfers.uploads)
			total_usersdown, filesdown = _num_users(self.np.transfers.downloads)
			total_usersup, filesup = _num_users(self.np.transfers.uploads)
			
		else:
			down = up = 0.0
			filesup = filesdown = total_usersdown = total_usersup = usersdown = usersup = 0
			
		self.DownloadUsers.set_text(_("Users: %s") % total_usersdown)
		self.UploadUsers.set_text(_("Users: %s") % total_usersup)
		self.DownloadFiles.set_text(_("Files: %s") % filesdown)
		self.UploadFiles.set_text(_("Files: %s") % filesup)
		
		self.DownStatus.pop(self.down_context_id)
		self.UpStatus.pop(self.up_context_id)
		self.DownStatus.push(self.down_context_id, _("Down: %(num)i users, %(speed).1f KB/s") % {'num':usersdown, 'speed':down})
		self.UpStatus.push(self.up_context_id, _("Up: %(num)i users, %(speed).1f KB/s") % {'num':usersup,'speed':up})
		self.TrayApp.SetToolTip(_("Nicotine+ Transfers: %(speeddown).1f KB/s Down, %(speedup).1f KB/s Up") % {'speeddown':down,'speedup':up})
	
	def BanUser(self, user):
		if self.np.transfers is not None:
			self.np.transfers.BanUser(user)
	
	def UnbanUser(self, user):
		if user in self.np.config.sections["server"]["banlist"]:
			self.np.config.sections["server"]["banlist"].remove(user)
			self.np.config.writeConfig()

	def IgnoreUser(self, user):
		if user not in self.np.config.sections["server"]["ignorelist"]:
			self.np.config.sections["server"]["ignorelist"].append(user)
			self.np.config.writeConfig()

	def UnignoreUser(self, user):
		if user in self.np.config.sections["server"]["ignorelist"]:
			self.np.config.sections["server"]["ignorelist"].remove(user)
			self.np.config.writeConfig()

	def OnAddUser(self, widget):
		text = widget.get_text()
		if not text:
			return
		widget.set_text("")
		self.userlist.AddToList(text)
		
	def BothRescan(self):
		self.OnRescan()
		if self.np.config.sections["transfers"]["enablebuddyshares"]:
			self.OnBuddyRescan()

		
	def OnRescan(self, widget = None, rebuild = False):
		if self.rescanning:
			return
		self.rescanning = 1
		
		self.rescan1.set_sensitive(False)
		self.rebuild1.set_sensitive(False)
		self.logMessage(_("Rescanning started"))
		
		shared = self.np.config.sections["transfers"]["shared"][:]
		if self.np.config.sections["transfers"]["sharedownloaddir"]:
			shared.append(self.np.config.sections["transfers"]["downloaddir"])
		cleanedshares = []
		for i in shared:
			if i not in cleanedshares:
				cleanedshares.append(i)
		msg = slskmessages.RescanShares(cleanedshares, lambda: None)
		thread.start_new_thread(self.np.RescanShares, (msg, rebuild))
		
	def OnRebuild(self, widget = None):
		self.OnRescan(widget, rebuild=True)
		
	def OnBuddyRescan(self, widget = None, rebuild = False):
		if self.brescanning:
			return
		self.brescanning = 1
		
		self.rescan_buddy.set_sensitive(False)
		self.rebuild_buddy.set_sensitive(False)
		self.logMessage(_("Rescanning Buddy Shares started"))
		
		shared = self.np.config.sections["transfers"]["buddyshared"][:] + self.np.config.sections["transfers"]["shared"][:]
		if self.np.config.sections["transfers"]["sharedownloaddir"]:
			shared.append(self.np.config.sections["transfers"]["downloaddir"])
		cleanedshares = []
		for i in shared:
			if i not in cleanedshares:
				cleanedshares.append(i)
		msg = slskmessages.RescanBuddyShares(cleanedshares, lambda: None)
		thread.start_new_thread(self.np.RescanBuddyShares, (msg, rebuild))
	
	def OnBuddyRebuild(self, widget = None):
		self.OnBuddyRescan(widget, rebuild=True)
	
		
	def _BuddyRescanFinished(self, data):
		self.np.config.setBuddyShares(*data)
		self.np.config.writeShares()
		
		self.rescan_buddy.set_sensitive(True)
		self.rebuild_buddy.set_sensitive(True)
		if self.np.transfers is not None:
			self.np.sendNumSharedFoldersFiles()
		self.brescanning = 0
		self.logMessage(_("Rescanning Buddy Shares finished"))
		self.BuddySharesProgress.hide()
		self.np.CompressShares("buddy")

	def _RescanFinished(self, data):
		self.np.config.setShares(*data)
		self.np.config.writeShares()
		
		self.rescan1.set_sensitive(True)
		self.rebuild1.set_sensitive(True)
		if self.np.transfers is not None:
			self.np.sendNumSharedFoldersFiles()
		self.rescanning = 0
		self.logMessage(_("Rescanning finished"))
		self.SharesProgress.hide()
		self.np.CompressShares("normal")
		
	def RescanFinished(self, data, type):
		if type == "buddy":
			gobject.idle_add(self._BuddyRescanFinished, data)
			
		elif type == "normal":
			gobject.idle_add(self._RescanFinished, data)
			
	
	def OnSettings(self, widget):
		self.settingswindow.SetSettings(self.np.config.sections)
		self.settingswindow.SettingsWindow.show()
	
	def OnSettingsClosed(self, widget, msg):
		if msg == "cancel":
			self.settingswindow.SettingsWindow.hide()
			return
		output = self.settingswindow.GetSettings()
		if type(output) is not tuple:
			return
		if msg == "ok":
			self.settingswindow.SettingsWindow.hide()
		needrescan, needcolors, needcompletion, config = output
		for (key, data) in config.items():
			self.np.config.sections[key].update(data)
		config = self.np.config.sections
		
		utils.DECIMALSEP = config["ui"]["decimalsep"]
		utils.CATCH_URLS = config["urls"]["urlcatching"]
		utils.HUMANIZE_URLS = config["urls"]["humanizeurls"]
		utils.PROTOCOL_HANDLERS = config["urls"]["protocols"].copy()
		utils.PROTOCOL_HANDLERS["slsk"] = self.OnSoulSeek
		utils.USERNAMEHOTSPOTS = config["ui"]["usernamehotspots"]
		uselimit = config["transfers"]["uselimit"]
		uploadlimit = config["transfers"]["uploadlimit"]
		limitby = config["transfers"]["limitby"]
		if config["transfers"]["geoblock"]:
			panic = config["transfers"]["geopanic"]
			cc = config["transfers"]["geoblockcc"]
			self.np.queue.put(slskmessages.SetGeoBlock([panic, cc]))
		else:
			self.np.queue.put(slskmessages.SetGeoBlock(None))
		self.np.queue.put(slskmessages.SetUploadLimit(uselimit,uploadlimit,limitby))
		self.np.ToggleRespondDistributed(settings=True)
		self.UpdateDownloadFilters()
		self.TransparentTint(1)
		self.np.config.writeConfig()
		if not config["ui"]["trayicon"] and self.TrayApp.HAVE_TRAYICON:
			self.TrayApp.destroy_trayicon()
		elif config["ui"]["trayicon"] and not self.TrayApp.HAVE_TRAYICON:
			if self.TrayApp.trayicon_module == None and not self.TrayApp.TRAYICON_CREATED:
				self.TrayApp.Load()
			else:
				self.TrayApp.HAVE_TRAYICON = True
				
			self.TrayApp.Draw()
		self.ChangeTranslation(config["language"]["language"])


		if needcompletion:
			self.chatrooms.roomsctrl.UpdateCompletions()
			self.privatechats.UpdateCompletions()
  	
		if needcolors:
			self.chatrooms.roomsctrl.UpdateColours()
			self.privatechats.UpdateColours()
			self.Searches.UpdateColours()
			self.downloads.UpdateColours()
			self.uploads.UpdateColours()
			self.userinfo.UpdateColours()
			self.userbrowse.UpdateColours()
			self.settingswindow.UpdateColours()
			self.UpdateColours()
  	
		self.OnHideChatButtons()

		for w in [self.ChatNotebook, self.PrivatechatNotebook, self.UserInfoNotebook, self.UserBrowseNotebook, self.SearchNotebook]:
			w.set_tab_closers(config["ui"]["tabclosers"])
			w.show_images(config["ui"]["tab_icons"])
			w.set_text_colors(None)
		
		tabLabels = [self.ChatTabLabel, self.PrivateChatTabLabel, self.DownloadsTabLabel, self.UploadsTabLabel, self.SearchTabLabel, self.UserInfoTabLabel, self.UserBrowseTabLabel, self.InterestsTabLabel]
		if "BuddiesTabLabel" in self.__dict__:
			tabLabels.append(self.BuddiesTabLabel)
			
		for label_tab in tabLabels:
			label_tab.show_image(config["ui"]["tab_icons"])
			label_tab.set_text_color(None)
		self.SetTabPositions()

		if self.np.transfers is not None:
			self.np.transfers.checkUploadQueue()
		self.UpdateTransferButtons()
		if needrescan:
			self.needrescan = 1
		
		if msg == "ok" and self.needrescan:
			self.needrescan = 0
			self.BothRescan()

		ConfigUnset = self.np.config.needConfig()
		if ConfigUnset > 1:
			if self.np.transfers is not None:
				self.connect1.set_sensitive(0)
			self.OnSettings(None)

		else:
			if self.np.transfers is None:
				self.connect1.set_sensitive(1)
		self.SetAllToolTips()
		
	def SetAllToolTips(self):
		act = self.np.config.sections["ui"]["tooltips"]
		for tips in [self.tooltips, self.roomlist.tooltips] + [page.tooltips for page in self.settingswindow.pages.values()] + [room.tooltips for room in self.chatrooms.roomsctrl.joinedrooms.values()] + [private.tooltips for private in self.privatechats.users.values()]  + [user.tooltips for user in self.userinfo.users.values()]  + [user.tooltips for user in self.userbrowse.users.values()] + [data[2].tooltips for data in self.Searches.searches.values() if data[2] is not None]:
			if act:
				tips.enable()
			else:
				tips.disable()
		
	def AutoReplace(self, message):
		if self.np.config.sections["words"]["replacewords"]:
			autoreplaced = self.np.config.sections["words"]["autoreplaced"]
			for word, replacement in autoreplaced.items():
				message = message.replace(word, replacement)
				
		return message
			
	def CensorChat(self, message):
		if self.np.config.sections["words"]["censorwords"]:
			filler = self.np.config.sections["words"]["censorfill"]
			censored = self.np.config.sections["words"]["censored"]
			for word in censored:
				message = message.replace(word, filler * len(word))
				
		return message
			
	def SetTabPositions(self):
		ui = self.np.config.sections["ui"]
		self.ChatNotebook.set_tab_pos(self.getTabPosition(ui["tabrooms"]))
		self.ChatNotebook.set_tab_angle(ui["labelrooms"])
		self.MainNotebook.set_tab_pos(self.getTabPosition(ui["tabmain"]))
		for label_tab in[self.ChatTabLabel, self.PrivateChatTabLabel, self.SearchTabLabel, self.UserInfoTabLabel, self.DownloadsTabLabel, self.UploadsTabLabel, self.UserBrowseTabLabel, self.InterestsTabLabel]:
			label_tab.set_angle(ui["labelmain"])
		if "BuddiesTabLabel" in self.__dict__:
			self.BuddiesTabLabel.set_angle(ui["labelmain"])
		self.PrivatechatNotebook.set_tab_pos(self.getTabPosition(ui["tabprivate"]))
		self.PrivatechatNotebook.set_tab_angle(ui["labelprivate"])
		self.UserInfoNotebook.set_tab_pos(self.getTabPosition(ui["tabinfo"]))
		self.UserInfoNotebook.set_tab_angle(ui["labelinfo"])
		self.UserBrowseNotebook.set_tab_pos(self.getTabPosition(ui["tabbrowse"]))
		self.UserBrowseNotebook.set_tab_angle(ui["labelbrowse"])
		self.SearchNotebook.set_tab_pos(self.getTabPosition(ui["tabsearch"]))
		self.SearchNotebook.set_tab_angle(ui["labelsearch"])
		
	def TransparentTint(self, update=None):

		if not self.np.config.sections["ui"]["enabletrans"]:
			if self.translux:
				self.translux.disable()
			return
	
		filter =""
		tint = None
		ttint = self.np.config.sections["ui"]["transtint"]
		
		if ttint == "" or ttint[0] != "#":
			return
		ttint = ttint[1:]
		if len(ttint) != 6:
			return
		try:

			alpha = "%02X" % self.np.config.sections["ui"]["transalpha"]
			tint = long(ttint+alpha, 16)
	
			if update and self.translux:
				self.translux.changeTint(tint)
				if self.LogWindow not in self.translux.subscribers.keys():
					self.translux.subscribe(self.LogWindow, lambda: self.LogWindow.get_window(gtk.TEXT_WINDOW_TEXT))
		except Exception, e:
			print e
		if self.translux is None and tint is not None:
			self.translux = translux.Translux(self.MainWindow, tint)
			
	def CreateIconButton(self, icon, icontype, callback, label=None):
		button = gtk.Button()
		button.connect_object("clicked", callback, "")
		button.show()
		
		Alignment = gtk.Alignment(0.5, 0.5, 0, 0)
		Alignment.show()
	
		Hbox = gtk.HBox(False, 2)
		Hbox.show()
		Hbox.set_spacing(2)
	
		image = gtk.Image()
		image.set_padding(0, 0)
		if icontype == "stock":
			image.set_from_stock(icon, 4)
		else:
			image.set_from_pixbuf(icon)
		image.show()
		Hbox.pack_start(image, False, False, 0)
		Alignment.add(Hbox)
		if label:
			Label = gtk.Label(label)
			Label.set_padding(0, 0)
			Label.show()
			Hbox.pack_start(Label, False, False, 0)
		button.add(Alignment)
		return button


	def UpdateDownloadFilters(self):
		proccessedfilters = []
		outfilter = "(\\\\("
		failed = {}
		df = self.np.config.sections["transfers"]["downloadfilters"]
		df.sort()
		# Get Filters from config file and check their escaped status
		# Test if they are valid regular expressions and save error messages
		
		for item in df :
			filter, escaped = item
			if escaped:
				dfilter = re.escape(filter)
				dfilter = dfilter.replace("\*", ".*")
			else:
				dfilter = filter
			try:
				re.compile("("+dfilter+")")
				outfilter += dfilter
				proccessedfilters.append(dfilter)
			except Exception, e:
				failed[dfilter] = e
					
			proccessedfilters.append(dfilter)
			
			if item is not df[-1]:
				outfilter += "|"
		# Crop trailing pipes
		while outfilter[-1] == "|":
			outfilter = outfilter [:-1]
		outfilter += ")$)"
		try:
			re.compile(outfilter)
			self.np.config.sections["transfers"]["downloadregexp"] = outfilter
			# Send error messages for each failed filter to log window
			if len(failed.keys()) >= 1:
				errors = ""
				for filter, error in failed.items():
					errors += "Filter: %s Error: %s " % (filter, error)
				error = _("Error: %(num)d Download filters failed! %(error)s " %{'num':len(failed.keys()), 'error':errors} )
				self.logMessage(error)
		except Exception, e:
			# Strange that individual filters _and_ the composite filter both fail
			self.logMessage(_("Error: Download Filter failed! Verify your filters. Reason: %s" % e))
			self.np.config.sections["transfers"]["downloadregexp"] = ""
		
	def UpdateTransferButtons(self):
		if self.np.config.sections["transfers"]["enabletransferbuttons"]:
			self.DownloadButtons.show()
			self.UploadButtons.show()
		else:
			self.UploadButtons.hide()
			self.DownloadButtons.hide()
			
	def OnNicotineGuide(self, widget):
		paths = []
		file = "NicotinePlusGuide.html"
		path1 = os.getcwd()
		path1split = path1.rsplit(os.sep, 1)

		if path1split[1] == "doc":
			paths.append(path1split[0])
		else:
			paths.append(path1)
		path2 = "%s/share/nicotine/documentation" % sys.prefix
		paths.append(path2)
		winpath = "C:\Program Files\Nicotine+" 
		paths.append(winpath)
		for path in paths:
			if os.path.exists(os.sep.join([path, "doc", file])):
				url = "file:%s/%s/%s" % (urllib.pathname2url(path).replace("|", ":") ,"doc", file)

				self.OpenUrl(url)
				return
		else:
			popupWarning(None, _("Cannot Find Guide"), _("The Nicotine Offline Guide ( NicotinePlusGuide.html ) was not found in either the following directories:\n\n<u>%(pwd)s\n</u><b>and</b>\n<u>%(prefix)s/share/nicotine/documentation/</u>\n\nEither install Nicotine-Plus, or start from inside the Nicotine-Plus source directory." % {'pwd':path1, 'prefix':sys.prefix } ) )
	
	def OnOnlineNicotineGuide(self, widget):
		url = "http://nicotine-plus.sourceforge.net/NicotinePlusGuide/"
		self.OpenUrl(url)
			
	def OnSourceForgeProject(self, widget):
		url = "http://sourceforge.net/projects/nicotine-plus/"
		self.OpenUrl(url)
		
	def OnTrac(self, widget):
		url = "http://nicotine-plus.org/"
		self.OpenUrl(url)
		
	def OpenUrl(self, url):
		if "http" in utils.PROTOCOL_HANDLERS:
			if utils.PROTOCOL_HANDLERS["http"].__class__ is utils.types.MethodType:
				utils.PROTOCOL_HANDLERS["http"](url)
			else:
				cmd = "%s &" % ( utils.PROTOCOL_HANDLERS["http"] % url)
				os.system(cmd)
		else:
			try:
				import gnomevfs
			except Exception, e:
				try:
					import gnome.vfs
				except Exception, e:
					pass
				else:
					gnome.url_show(url)
			else:
				gnome.url_show(url)
				
	def OnAbout(self, widget):
		dlg = AboutDialog(self.MainWindow, self)
		dlg.run()
		dlg.destroy()

	def OnAboutChatroomCommands(self, widget, parent=None):
		if parent is None:
			parent = self.MainWindow
		dlg = AboutRoomsDialog(parent)
		dlg.run()
		dlg.destroy()
	
	def OnAboutPrivateChatCommands(self, widget):
		dlg = AboutPrivateDialog(self.MainWindow)
		dlg.run()
		dlg.destroy()
		
	def OnAboutDependencies(self, widget):
		dlg = AboutDependenciesDialog(self.MainWindow)
		dlg.run()
		dlg.destroy()
	
	def OnAboutFilters(self, widget):
		dlg = AboutFiltersDialog(self.MainWindow)
		dlg.run()
		dlg.destroy()
		
	def OnHideChatButtons(self, widget=None):
		if widget is not None:
			hide = widget.get_active()
			self.np.config.sections["ui"]["chat_hidebuttons"] = hide
		if self.chatrooms is None:
			return
		for room in self.chatrooms.roomsctrl.joinedrooms.values():
			room.OnHideChatButtons(self.np.config.sections["ui"]["chat_hidebuttons"])

		self.np.config.writeConfig()
		
	def OnHideLog(self, widget):
		active = widget.get_active()
		self.np.config.sections["logging"]["logcollapsed"] = active
		if active:
			if self.LogScrolledWindow in self.vpaned1.get_children():
				self.vpaned1.remove(self.LogScrolledWindow)
		else:
			if not self.LogScrolledWindow in self.vpaned1.get_children():
				self.vpaned1.pack2(self.LogScrolledWindow, False, True)
				ScrollBottom(self.LogScrolledWindow)
		self.np.config.writeConfig()
	
	def OnHideFlags(self, widget):
		active = widget.get_active()
		self.np.config.sections["columns"]["hideflags"] = active
		for room in self.chatrooms.roomsctrl.joinedrooms:
			self.chatrooms.roomsctrl.joinedrooms[room].cols[1].set_visible(int(not active))
			self.np.config.sections["columns"]["chatrooms"][room][1] = int(not active)
		self.userlist.cols[1].set_visible(int(not active))
		self.np.config.sections["columns"]["userlist"][1] = int(not active)
		self.np.config.writeConfig()
		
	def OnHideRoomList(self, widget):
		active = widget.get_active()
		self.np.config.sections["ui"]["roomlistcollapsed"] = active
		if active:
			if self.roomlist.vbox2 in self.vpaned3.get_children():
				self.vpaned3.remove(self.roomlist.vbox2)
			if not self.buddylist_in_chatrooms1.get_active():
				self.vpaned3.hide()
		else:
			if not self.roomlist.vbox2 in self.vpaned3.get_children():
				self.vpaned3.pack2(self.roomlist.vbox2, True, True)
				self.vpaned3.show()
		self.np.config.writeConfig()
		
	def OnToggleBuddyList(self, widget):
		active = widget.get_active()
		self.np.config.sections["ui"]["buddylistinchatrooms"] = active
		if active:
			self.vpaned3.show()
			if self.userlistvbox in self.MainNotebook.get_children():
				self.MainNotebook.remove_page(8)
			if self.userlistvbox not in self.vpaned3.get_children():
				self.vpaned3.pack1(self.userlistvbox, True, True)
			self.BuddiesLabel.show()
				
		else:
			if self.hide_room_list1.get_active():
				self.vpaned3.hide()
			if self.userlistvbox in self.vpaned3.get_children():
				self.vpaned3.remove(self.userlistvbox)
			self.BuddiesTabLabel = ImageLabel(_("Buddy list"), self.images["empty"])
			#self.get_custom_widget("BuddiesTabLabel", "ImageLabel", _("Buddy list"), 0, 0)
			self.BuddiesTabLabel.show()
			if self.userlistvbox not in self.MainNotebook.get_children():
				self.MainNotebook.append_page(self.userlistvbox, self.BuddiesTabLabel)
			self.BuddiesLabel.hide()

		self.np.config.writeConfig()
		
	def OnCheckPrivileges(self, widget):
		self.np.queue.put(slskmessages.CheckPrivileges())
	
	def OnSoulSeek(self, url):
		try:
			user, file = urllib.url2pathname(url[7:]).split("/", 1)
			if file[-1] == "/":
				self.np.ProcessRequestToPeer(user, slskmessages.FolderContentsRequest(None, file[:-1].replace("/","\\")))
			else:
				self.np.transfers.getFile(user, file.replace("/","\\"), "")
		except:
			self.logMessage(_("Invalid SoulSeek meta-url: %s") % url)

	def SetClipboardURL(self, user, path):
		self.clip.set_text( "slsk://" + urllib.pathname2url("%s/%s" % (user, path.replace("\\", "/"))) )
		self.clip_data = "slsk://" + urllib.pathname2url("%s/%s" % (user, path.replace("\\", "/")))
		self.MainWindow.selection_owner_set("PRIMARY", 0L)


	def OnSelectionGet(self, widget, data, info, timestamp):
		data.set_text(self.clip_data, -1)

	def LocalUserInfoRequest(self, user):
		# Hack for local userinfo requests, for extra security
		if user == self.np.config.sections["server"]["login"]:
			try:
				if self.np.config.sections["userinfo"]["pic"] != "":
					if sys.platform == "win32":
						userpic = u"%s" % self.np.config.sections["userinfo"]["pic"]
					else:
						userpic = self.np.config.sections["userinfo"]["pic"]
					if os.path.exists(userpic):
						has_pic = True
						f=open(userpic,'rb')
						pic = f.read()
						f.close()
					else:
						has_pic = False
						pic = None
				else:
					has_pic = False
					pic = None
				
			except:
				pic = None
			descr = self.np.encode(eval(self.np.config.sections["userinfo"]["descr"], {}))
			
			if self.np.transfers is not None:
				
				totalupl = self.np.transfers.getTotalUploadsAllowed()
				queuesize = self.np.transfers.getUploadQueueSizes()[0]
				slotsavail = not self.np.transfers.bandwidthLimitReached()
				ua = self.np.config.sections["transfers"]["remotedownloads"]
				if ua:
					uploadallowed = self.np.config.sections["transfers"]["uploadallowed"]
				else:
					uploadallowed = ua
				self.userinfo.ShowLocalInfo(user, descr, has_pic, pic, totalupl, queuesize, slotsavail, uploadallowed)
			
		else:
			self.np.ProcessRequestToPeer(user, slskmessages.UserInfoRequest(None), self.userinfo)
				
	
	# Here we go, ugly hack for getting your own shares
	def BrowseUser(self, user):
		login = self.np.config.sections["server"]["login"]
		if user is None or user == login:
			user = login
			if user in [i[0] for i in self.np.config.sections["server"]["userlist"]] and self.np.config.sections["transfers"]["enablebuddyshares"]:
				m = slskmessages.SharedFileList(None, self.np.config.sections["transfers"]["bsharedfilesstreams"])
			else:
				m = slskmessages.SharedFileList(None, self.np.config.sections["transfers"]["sharedfilesstreams"])
			m.parseNetworkMessage(m.makeNetworkMessage(nozlib=1), nozlib=1)
			self.userbrowse.ShowInfo(login, m)
		else:
			self.np.ProcessRequestToPeer(user, slskmessages.GetSharedFileList(None), self.userbrowse)

	def OnBrowseMyShares(self, widget):
		self.BrowseUser(None)

	def OnCheckLatest(self, widget):
		checklatest(self.MainWindow)

	def OnFocusIn(self, widget, event):
		self.MainWindow.set_icon(self.images["n"])
		self.got_focus = True
	
	def OnFocusOut(self, widget, event):
		self.got_focus = False
		
	def EntryCompletionFindMatch(self, completion, entry_text, iter, widget):
		model = completion.get_model()
		item_text = model.get_value(iter, 0)
		ix = widget.get_position()
		config = self.np.config.sections["words"]
		
		if entry_text == None or entry_text == "" or entry_text.isspace() or item_text is None:
			return False
		# Get word to the left of current position
		if " " in entry_text:
			split_key = entry_text[:ix].split(" ")[-1]
		else:
			split_key = entry_text
		if split_key.isspace() or split_key == "" or len(split_key) < config["characters"]:
			return False
		# case-insensitive matching
		if item_text.lower().startswith(split_key) and item_text.lower() != split_key:
			return True
		return False
#
	def EntryCompletionFoundMatch(self, completion, model, iter, widget):
		current_text = widget.get_text()
		ix = widget.get_position()
		# if more than a word has been typed, we throw away the
		# one to the left of our current position because we want
		# to replace it with the matching word
		
		if " " in current_text:
			prefix = " ".join(current_text[:ix].split(" ")[:-1])
			suffix = " ".join(current_text[ix:].split(" "))

			# add the matching word
			new_text = "%s %s%s" % (prefix, model[iter][0], suffix)
			# set back the whole text
			widget.set_text(new_text)
			# move the cursor at the end
			widget.set_position(len(prefix) + len(model[iter][0]) + 1)
		else:
			new_text = "%s" % (model[iter][0])
			widget.set_text(new_text)
			widget.set_position(-1)
		# stop the event propagation
		return True
		
	def OnPopupLogMenu(self, widget, event):
		if event.button != 3:
			return False
		widget.emit_stop_by_name("button-press-event")
		self.logpopupmenu.popup(None, None, None, event.button, event.time)
		return True
	
	def OnFindLogWindow(self, widget):

		self.OnFindTextview(widget, self.LogWindow)
				
	def OnFindTextview(self, widget, textview):

		if "FindDialog" not in self.__dict__:
			self.FindDialog = FindDialog(self, _('Enter the string to search for:'), "", textview=textview, modal=False)
			self.FindDialog.set_title(_('Nicotine+: Find string'))
			self.FindDialog.set_icon(self.images["n"])
			self.FindDialog.set_default_size(300, 100)
			self.FindDialog.show()
			
			self.FindDialog.connect("find-click", self.OnFindClicked)
			return
		
		self.FindDialog.textview = textview
		self.FindDialog.currentPosition = None
		self.FindDialog.nextPosition = None
		self.FindDialog.entry.set_text("")
		self.FindDialog.show()

		
	def OnFindClicked(self, widget, direction):

		if self.FindDialog.textview is None:
			return
		textview = self.FindDialog.textview
		buffer = textview.get_buffer()
		start, end = buffer.get_bounds()
		query = self.FindDialog.query
		
		textview.emit("select-all", False)
		if self.FindDialog.currentPosition is None:

			self.FindDialog.currentPosition = buffer.create_mark(None, start, False)
			self.FindDialog.nextPosition = buffer.create_mark(None, start, False)
		second = 0
		if direction == "next":
			current = buffer.get_mark("insert")
			iter = buffer.get_iter_at_mark(current)
			match1 = iter.forward_search(query, gtk.TEXT_SEARCH_TEXT_ONLY, limit=None)
			if match1 is not None and len(match1) == 2:
				
				match_start, match_end = match1
				buffer.place_cursor(match_end)
				buffer.select_range( match_end, match_start)
				textview.scroll_to_iter(match_start, 0)
		
		elif direction == "previous":
			current = buffer.get_mark("insert")
			iter = buffer.get_iter_at_mark(current)
			match1 = iter.backward_search(query, gtk.TEXT_SEARCH_TEXT_ONLY, limit=None)
			if match1 is not None and len(match1) == 2:
				
				match_start, match_end = match1
				buffer.place_cursor(match_start)
				buffer.select_range(match_start, match_end)
				textview.scroll_to_iter(match_start, 0)
			return
	

	def OnCopyLogWindow(self, widget):
		bound = self.LogWindow.get_buffer().get_selection_bounds()
		if bound is not None and len(bound) == 2:
			start, end = bound
			log = self.LogWindow.get_buffer().get_text(start, end)
			self.clip.set_text(log)
			
	def OnCopyAllLogWindow(self, widget):
		start, end = self.LogWindow.get_buffer().get_bounds()
		log = self.LogWindow.get_buffer().get_text(start, end)
		self.clip.set_text(log)
		
	def OnClearLogWindow(self, widget):
		self.LogWindow.get_buffer().set_text("")

	def OnAddThingILike(self, widget):
		thing = utils.InputDialog(self.MainWindow, _("Add thing I like"), _("I like")+":")
		if thing and thing.lower() not in self.np.config.sections["interests"]["likes"]:
			thing = thing.lower()
			self.np.config.sections["interests"]["likes"].append(thing)
			self.likes[thing] = self.likeslist.append([thing])
			self.np.config.writeConfig()
			self.np.queue.put(slskmessages.AddThingILike(self.np.encode(thing)))

	def OnAddThingIDislike(self, widget):
		thing = utils.InputDialog(self.MainWindow, _("Add thing I don't like"), _("I don't like")+":")
		if thing and thing.lower() not in self.np.config.sections["interests"]["dislikes"]:
			thing = thing.lower()
			self.np.config.sections["interests"]["dislikes"].append(thing)
			self.dislikes[thing] = self.dislikeslist.append([thing])
			self.np.config.writeConfig()
			self.np.queue.put(slskmessages.AddThingIHate(self.np.encode(thing)))

	def SetRecommendations(self, title, recom):
		self.recommendationslist.clear()
		for thing in recom.keys():
			rating = recom[thing]
			thing = self.np.decode(thing)
			self.recommendationslist.append([thing, Humanize(rating), rating])
		self.recommendationslist.set_sort_column_id(2, gtk.SORT_DESCENDING)
		
	def SetUnrecommendations(self, title, recom):
		self.unrecommendationslist.clear()
		for thing in recom.keys():
			rating = recom[thing]
			thing = self.np.decode(thing)
			self.unrecommendationslist.append([thing, Humanize(rating), rating])
		self.unrecommendationslist.set_sort_column_id(2, gtk.SORT_ASCENDING)
		
	def GlobalRecommendations(self, msg):
		self.SetRecommendations("Global recommendations", msg.recommendations)
		self.SetUnrecommendations("Unrecommendations", msg.unrecommendations)

	def Recommendations(self, msg):
		self.SetRecommendations("Recommendations", msg.recommendations)
		self.SetUnrecommendations("Unrecommendations", msg.unrecommendations)

	def ItemRecommendations(self, msg):
		self.SetRecommendations(_("Recommendations for %s") % msg.thing, msg.recommendations)
		self.SetUnrecommendations("Unrecommendations", msg.unrecommendations)

	def OnGlobalRecommendationsClicked(self, widget):
		self.np.queue.put(slskmessages.GlobalRecommendations())

	def OnRecommendationsClicked(self, widget):
		self.np.queue.put(slskmessages.Recommendations())

	def OnSimilarUsersClicked(self, widget):
		self.np.queue.put(slskmessages.SimilarUsers())

	def SimilarUsers(self, msg):
		self.recommendationuserslist.clear()
		self.recommendationusers = {}
		for user in msg.users.keys():
			iter = self.recommendationuserslist.append([self.images["offline"], user, "0", "0", 0, 0, 0])
			self.recommendationusers[user] = iter
			self.np.queue.put(slskmessages.AddUser(user))


	def ItemSimilarUsers(self, msg):
		self.recommendationuserslist.clear()
		self.recommendationusers = {}
		for user in msg.users:
			iter = self.recommendationuserslist.append([self.images["offline"], user, "0", "0", 0, 0, 0])
			self.recommendationusers[user] = iter
			self.np.queue.put(slskmessages.AddUser(user))

	def GetUserStatus(self, msg):
		if msg.user not in self.recommendationusers:
			return
		img = self.GetStatusImage(msg.status)
		self.recommendationuserslist.set(self.recommendationusers[msg.user], 0, img, 4, msg.status)

	def GetUserStats(self, msg):
		if msg.user not in self.recommendationusers:
			return
		self.recommendationuserslist.set(self.recommendationusers[msg.user], 2, Humanize(msg.avgspeed), 3, Humanize(msg.files), 5, msg.avgspeed, 6, msg.files)

	def OnPopupRUMenu(self, widget, event):
		items = self.ru_popup_menu.get_children()
		d = self.RecommendationUsersList.get_path_at_pos(int(event.x), int(event.y))
		if not d:
			return
		path, column, x, y = d
		user = self.recommendationuserslist.get_value(self.recommendationuserslist.get_iter(path), 1)
		if event.button != 3:
			if event.type == gtk.gdk._2BUTTON_PRESS:
				self.privatechats.SendMessage(user)
				self.MainNotebook.set_current_page(1)
			return
		self.ru_popup_menu.set_user(user)
		items[7].set_active(user in [i[0] for i in self.np.config.sections["server"]["userlist"]])
		items[8].set_active(user in self.np.config.sections["server"]["banlist"])
		items[9].set_active(user in self.np.config.sections["server"]["ignorelist"])
		self.ru_popup_menu.popup(None, None, None, event.button, event.time)

	def OnRemoveThingILike(self, widget):
		thing = self.til_popup_menu.get_user()
		if thing not in self.np.config.sections["interests"]["likes"]:
			return
		self.likeslist.remove(self.likes[thing])
		del self.likes[thing]
		self.np.config.sections["interests"]["likes"].remove(thing)
		self.np.config.writeConfig()
		self.np.queue.put(slskmessages.RemoveThingILike(self.np.encode(thing)))
	
	def OnRecommendItem(self, widget):
		thing = self.til_popup_menu.get_user()
		self.np.queue.put(slskmessages.ItemRecommendations(self.np.encode(thing)))
		self.np.queue.put(slskmessages.ItemSimilarUsers(self.np.encode(thing)))
	
	def OnPopupTILMenu(self, widget, event):
		if event.button != 3:
			return
		d = self.LikesList.get_path_at_pos(int(event.x), int(event.y))
		if not d:
			return
		path, column, x, y = d
		iter = self.likeslist.get_iter(path)
		thing = self.likeslist.get_value(iter, 0)
		self.til_popup_menu.set_user(thing)
		self.til_popup_menu.popup(None, None, None, event.button, event.time)

	def OnRemoveThingIDislike(self, widget):
		thing = self.tidl_popup_menu.get_user()
		if thing not in self.np.config.sections["interests"]["dislikes"]:
			return
		self.dislikeslist.remove(self.dislikes[thing])
		del self.dislikes[thing]
		self.np.config.sections["interests"]["dislikes"].remove(thing)
		self.np.config.writeConfig()
		self.np.queue.put(slskmessages.RemoveThingIHate(self.np.encode(thing)))
	
	def OnPopupTIDLMenu(self, widget, event):
		if event.button != 3:
			return
		d = self.DislikesList.get_path_at_pos(int(event.x), int(event.y))
		if not d:
			return
		path, column, x, y = d
		iter = self.dislikeslist.get_iter(path)
		thing = self.dislikeslist.get_value(iter, 0)
		self.tidl_popup_menu.set_user(thing)
		self.tidl_popup_menu.popup(None, None, None, event.button, event.time)

	def OnLikeRecommendation(self, widget):
		thing = widget.parent.get_user()
		if widget.get_active() and thing not in self.np.config.sections["interests"]["likes"]:
			self.np.config.sections["interests"]["likes"].append(thing)
			self.likes[thing] = self.likeslist.append([thing])
			self.np.config.writeConfig()
			self.np.queue.put(slskmessages.AddThingILike(self.np.encode(thing)))
		elif not widget.get_active() and thing in self.np.config.sections["interests"]["likes"]:
			self.likeslist.remove(self.likes[thing])
			del self.likes[thing]
			self.np.config.sections["interests"]["likes"].remove(thing)
			self.np.config.writeConfig()
			self.np.queue.put(slskmessages.RemoveThingILike(self.np.encode(thing)))

	def OnDislikeRecommendation(self, widget):
		thing = widget.parent.get_user()
		if widget.get_active() and thing not in self.np.config.sections["interests"]["dislikes"]:
			self.np.config.sections["interests"]["dislikes"].append(thing)
			self.dislikes[thing] = self.dislikeslist.append([thing])
			self.np.config.writeConfig()
			self.np.queue.put(slskmessages.AddThingIHate(self.np.encode(thing)))
		elif not widget.get_active() and thing in self.np.config.sections["interests"]["dislikes"]:
			self.dislikeslist.remove(self.dislikes[thing])
			del self.dislikes[thing]
			self.np.config.sections["interests"]["dislikes"].remove(thing)
			self.np.config.writeConfig()
			self.np.queue.put(slskmessages.RemoveThingIHate(self.np.encode(thing)))

	def OnRecommendRecommendation(self, widget):
		thing = self.r_popup_menu.get_user()
		self.np.queue.put(slskmessages.ItemRecommendations(self.np.encode(thing)))
		self.np.queue.put(slskmessages.ItemSimilarUsers(self.np.encode(thing)))

	def OnRecommendSearch(self, widget):
		thing = widget.parent.get_user()
		self.SearchEntry.set_text(thing)
		self.MainNotebook.set_current_page(4)

	def OnPopupRMenu(self, widget, event):
		if event.button != 3:
			return
		d = self.RecommendationsList.get_path_at_pos(int(event.x), int(event.y))
		if not d:
			return
		path, column, x, y = d
		iter = self.recommendationslist.get_iter(path)
		thing = self.recommendationslist.get_value(iter, 0)
		items = self.r_popup_menu.get_children()
		self.r_popup_menu.set_user(thing)
		items[0].set_active(thing in self.np.config.sections["interests"]["likes"])
		items[1].set_active(thing in self.np.config.sections["interests"]["dislikes"])
		self.r_popup_menu.popup(None, None, None, event.button, event.time)

	def OnPopupUnRecMenu(self, widget, event):
		if event.button != 3:
			return
		d = self.UnrecommendationsList.get_path_at_pos(int(event.x), int(event.y))
		if not d:
			return
		path, column, x, y = d
		iter = self.unrecommendationslist.get_iter(path)
		thing = self.unrecommendationslist.get_value(iter, 0)
		items = self.ur_popup_menu.get_children()
		self.ur_popup_menu.set_user(thing)
		items[0].set_active(thing in self.np.config.sections["interests"]["likes"])
		items[1].set_active(thing in self.np.config.sections["interests"]["dislikes"])
		self.ur_popup_menu.popup(None, None, None, event.button, event.time)
		
	def OnHideTickers(self, widget):
		if not self.chatrooms:
			return
		hide = widget.get_active()
		self.np.config.sections["ticker"]["hide"] = hide
		self.np.config.writeConfig()
		for room in self.chatrooms.roomsctrl.joinedrooms.values():
			room.ShowTicker(not hide)
			
	def RecommendationsExpanderStatus(self, widget):
		if widget.get_property("expanded"):
			self.RecommendationsVbox.set_child_packing(widget, False, True, 0, 0)
		else:
			self.RecommendationsVbox.set_child_packing(widget, True, True, 0, 0)
			
	def GivePrivileges(self, user, days):
		self.np.queue.put(slskmessages.GivePrivileges(user, days))
		
	def OnChatRooms(self, widget):
		self.MainNotebook.set_current_page(0)
	
	def OnPrivateChat(self, widget):
		self.MainNotebook.set_current_page(1)
	
	def OnDownloads(self, widget):
		self.MainNotebook.set_current_page(2)
	
	def OnUploads(self, widget):
		self.MainNotebook.set_current_page(3)
	
	def OnSearchFiles(self, widget):
		self.MainNotebook.set_current_page(4)
	
	def OnUserInfo(self, widget):
		self.MainNotebook.set_current_page(5)
	
	def OnUserBrowse(self, widget):
		self.MainNotebook.set_current_page(6)
	
	def OnInterests(self, widget):
		self.MainNotebook.set_current_page(7)
	
	def OnUserList(self, widget):
		self.MainNotebook.set_current_page(8)

class TrayApp:
	def __init__(self, frame):
		self.frame = frame
		self.frame.is_mapped = 1
		self.current_image = None
		self.pygtkicon = False
		if gtk.pygtk_version[0] >= 2 and gtk.pygtk_version[1] >= 10:
			self.pygtkicon = True
		self.trayicon = None
		self.trayicon_module = None
		self.TRAYICON_CREATED = 0
		self.TRAYICON_FAILED = 0
		self.CREATE_TRAYICON = 0
		self.HAVE_TRAYICON = False
		self.tray_status = {"hilites" : { "rooms": [], "private": [] }, "status": "disconnect", "last": "disconnect"}
		self.CreateMenu()
				
	def HideUnhideWindow(self, widget):
		if self.frame.is_mapped:
			self.frame.MainWindow.unmap()
			self.frame.is_mapped = 0
		else:
						
			self.frame.MainWindow.map()
			# weird, but this allows us to easily a minimized nicotine from one
			# desktop to another by clicking on the tray icon
			if self.frame.minimized:
				self.frame.MainWindow.present()
			self.frame.MainWindow.grab_focus()
			self.frame.is_mapped = 1
   			self.frame.chatrooms.roomsctrl.ClearNotifications()
			self.frame.privatechats.ClearNotifications()
			
	def Create(self):
		if self.CREATE_TRAYICON:
			self.Load()
		if self.HAVE_TRAYICON:
			self.Draw()
			
	def Load(self):
		if self.TRAYICON_FAILED:
			return

		# PyGTK >= 2.10
		if self.pygtkicon:
			trayicon = gtk.StatusIcon()
			self.trayicon_module = trayicon
			self.HAVE_TRAYICON = True
			self.TRAYICON_FAILED = False
		else:
			if sys.platform == "win32":
				return
			try:
				from pynicotine import trayicon
				self.trayicon_module = trayicon
				self.HAVE_TRAYICON = True
				self.TRAYICON_FAILED = False
			except ImportError, error:
				self.TRAYICON_FAILED = True
				self.HAVE_TRAYICON = False
				message = _("Note: Trayicon Python module was not found in the pynicotine directory: %s") % error
				print message
				self.frame.logMessage(message)
			
	def destroy_trayicon(self):
		if not self.TRAYICON_CREATED:
			return
		self.TRAYICON_CREATED = 0
		self.HAVE_TRAYICON = False
		self.current_image = None
		
		
		if self.pygtkicon:
			self.trayicon_module.set_visible(False)
			self.trayicon_module = None
		else:
			if sys.platform != "win32":
				self.eventbox.destroy()
				self.trayicon.destroy()
			else:
				self.tray_status["last"] = ""
				self.trayicon.hide_icon()
		
		self.tray_popup_menu.destroy()

		
	def Draw(self):
		if not self.HAVE_TRAYICON or self.trayicon_module == None or self.TRAYICON_CREATED:
			return
		self.TRAYICON_CREATED = 1
	
		

		if self.pygtkicon:
			self.trayicon_module.set_visible(True)
			self.trayicon_module.connect("popup-menu", self.OnStatusIconPopup)
			self.trayicon_module.connect("activate", self.OnStatusIconClicked)
			
		else:
			if sys.platform == "win32":
				if not self.trayicon:
					self.trayicon = self.trayicon_module.TrayIcon("Nicotine", self.frame)
				self.trayicon.show_icon()
				
			else:
				self.trayicon = self.trayicon_module.TrayIcon("Nicotine")
				self.eventbox = gtk.EventBox()
				self.trayicon.add(self.eventbox)
				self.eventbox.connect("button-press-event", self.OnTrayiconClicked)
				self.trayicon.show_all()
	
			
		self.SetImage(self.tray_status["status"])

					
	def SetImage(self, status=None):
		# Abort if Trayicon module wasn't loaded
		if not self.HAVE_TRAYICON or self.trayicon_module == None or not self.TRAYICON_CREATED:
			return
		try:
			if status != None:
				self.tray_status["status"] = status
			# Check for hilites, and display hilite icon if there is a room or private hilite
			if self.tray_status["hilites"]["rooms"] == [] and self.tray_status["hilites"]["private"] == []:
				# If there is no hilite, display the status
				icon = self.tray_status["status"]
			else:
				icon = "hilite2"

			if icon != self.tray_status["last"]:
				self.tray_status["last"] = icon

			
			if self.pygtkicon:
				self.trayicon_module.set_from_pixbuf(self.frame.images[icon])
			else:
				if sys.platform == "win32":
					# For Win32 Systray 
					self.trayicon.set_img(icon)
				else:
					# For trayicon.so module X11 Systray 
					self.eventbox.hide()
					if self.current_image != None:
						self.eventbox.remove(self.current_image)
				
					img = gtk.Image()
					img.set_from_pixbuf(self.frame.images[icon])
					img.show()
	
					self.current_image = img
					self.eventbox.add(self.current_image)
					self.eventbox.show()
		except Exception,e:
			print "ERROR: SetImage", e
			
	def CreateMenu(self):
		try:

			self.tray_popup_menu_server = popup0 = PopupMenu(self)
			popup0.setup(
				("#" + _("Connect"), self.frame.OnConnect, gtk.STOCK_CONNECT),
				("#" + _("Disconnect"), self.frame.OnDisconnect, gtk.STOCK_DISCONNECT),
			)
			self.tray_popup_menu = popup = PopupMenu(self)
			popup.setup(
				("#" + _("Hide / Unhide Nicotine"), self.HideUnhideWindow, gtk.STOCK_GOTO_BOTTOM),
				(1, _("Server"), self.tray_popup_menu_server, self.OnPopupServer),
				("#" + _("Settings"), self.frame.OnSettings, gtk.STOCK_PREFERENCES),
				("#" + _("Send Message"), self.frame.OnOpenPrivateChat, gtk.STOCK_EDIT),
				("#" + _("Lookup a User's IP"), self.frame.OnGetAUsersIP, gtk.STOCK_NETWORK),
				("#" + _("Lookup a User's Info"), self.frame.OnGetAUsersInfo, gtk.STOCK_DIALOG_INFO),
				("#" + _("Lookup a User's Shares"), self.frame.OnGetAUsersShares, gtk.STOCK_HARDDISK),
				("%" + _("Toggle Away"), self.frame.OnAway, self.frame.images["away2"] ),
				("#" + _("Quit"), self.frame.OnExit, gtk.STOCK_QUIT),
			)
		
		except Exception,e:
			print "ERROR: tray menu", e
			
	def OnPopupServer(self, widget):
		items = self.tray_popup_menu_server.get_children()
		
		
		if self.tray_status["status"] == "disconnect":
			items[0].set_sensitive(True)
			items[1].set_sensitive(False)
		else:
			items[0].set_sensitive(False)
			items[1].set_sensitive(True)
		return

	def OnStatusIconClicked(self, status_icon):
		self.HideUnhideWindow(None)
		
	def OnStatusIconPopup(self, status_icon, button, activate_time):
		if button == 3:
			self.tray_popup_menu.popup(None, None, None, button, activate_time)
		
	def OnTrayiconClicked(self, obj, event):
		(w, h) = self.trayicon.get_size()
		if event.x < 0 or event.y < 0 or event.x >= w or event.y >= h:
			return

		if event.button == 1:
			self.HideUnhideWindow(None)
		else:
			items = self.tray_popup_menu.get_children()
			if self.tray_status["status"] == "disconnect":
				act = False
			else:
				act = True
			items[3].set_sensitive(act)
			items[4].set_sensitive(act)
			items[5].set_sensitive(act)
			items[6].set_sensitive(act)
			items[7].set_sensitive(act)
			if event.type == gtk.gdk.BUTTON_PRESS:
				self.tray_popup_menu.popup(None, None, None, event.button, event.time)
				return True
			return False
			
	def SetToolTip(self, string):
		if self.pygtkicon and self.trayicon_module is not None:
   			self.trayicon_module.set_tooltip(string)
		
class gstreamer:
	def __init__(self):
		self.player = None
		try:
			import pygst
			pygst.require("0.10")
			import gst
		except Exception, error:
			#print _("WARNING: Gstreamer-python module failed to load:"), error
			return
		self.gst = gst
		try:
			self.player = gst.element_factory_make("playbin", "player")
			fakesink = gst.element_factory_make('fakesink', "my-fakesink")
			self.player.set_property("video-sink", fakesink)
		except Exception, error:
			print _("ERROR: Gstreamer-python could not play:"), error
			self.gst = self.player = None
			return
		
		self.bus = self.player.get_bus()
		self.bus.add_signal_watch()
		self.bus.connect('message', self.on_gst_message)

	def play(self, path):
		self.player.set_property('uri', "file://" + path)
		self.player.set_state(self.gst.STATE_PLAYING)

	def on_gst_message(self, bus, message):
		t = message.type
		if t == self.gst.MESSAGE_EOS:
			self.player.set_state(self.gst.STATE_NULL)
			
		elif t == self.gst.MESSAGE_ERROR:
			self.player.set_state(self.gst.STATE_NULL)
			
class MainApp:
	def __init__(self, config, trayicon):
		self.frame = NicotineFrame(config, trayicon)
	
	def MainLoop(self):
		signal.signal(signal.SIGINT, signal.SIG_IGN)
		self.frame.MainWindow.show()
		gtk.gdk.threads_init()
		gtk.gdk.threads_enter()
		gtk.main()
		gtk.gdk.threads_leave()
