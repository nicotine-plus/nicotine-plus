# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
import os

#import gtkexcepthook

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
import utils
from utils import AppendLine, ImageLabel, IconNotebook, ScrollBottom, PopupMenu, Humanize, popupWarning
import translux
from dirchooser import ChooseFile
from pynicotine.utils import _
import nowplaying
from entrydialog import  *


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

class NicotineFrame(MainWindow):
	def __init__(self, config, use_trayicon):
		self.images = {}
		self.clip_data = ""
		self.configfile = config

		self.chatrooms = None
		
		self.got_focus = False
		self.importimages()
		if sys.platform == "win32":
			import icondata
		config2 = Config(config)
		config2.readConfig()
		# For Win32 Systray 
		if sys.platform == "win32":
			self.icons = {}
			for i in "hilite2", "connect", "disconnect", "away2":
				if "icontheme"  in config2.sections["ui"]:
					path = os.path.expanduser(os.path.join(config2.sections["ui"]["icontheme"], i +".ico"))
					if os.path.exists(path):
						data = open(path, 'rb')
						s = data.read()
						data.close()
						self.icons[i] = s
						del s
						continue
					else:
						# default icons
						data = getattr(icondata, i)
				else:
					# default icons
					data = getattr(icondata, i)
				self.icons[i] = data
		for i in "empty", "away", "online", "offline", "hilite", "hilite2", "connect", "disconnect", "away2", "n":
			loader = gtk.gdk.PixbufLoader("png")
			if "icontheme" in config2.sections["ui"]:
				path = os.path.expanduser(os.path.join(config2.sections["ui"]["icontheme"], i +".png"))
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
		self.trayicon = None
		self.trayicon_module = None
		self.TRAYICON_CREATED = 0
		self.TRAYICON_FAILED = 0
		self.CREATE_TRAYICON = 0
		if use_trayicon and config2.sections["ui"]["trayicon"]:
			self.CREATE_TRAYICON = 1
			
		else:
			self.HAVE_TRAYICON = 0
		del data
		
		
		MainWindow.__init__(self)
		self.MainWindow.set_title(_("Nicotine+") + " " + version)
		self.MainWindow.set_icon(self.images["n"])
		self.MainWindow.selection_add_target("PRIMARY", "STRING", 1)
		self.MainWindow.set_geometry_hints(None, min_width=500, min_height=500)
		self.MainWindow.connect("configure_event", self.OnWindowChange)
		width = config2.sections["ui"]["width"]
		height = config2.sections["ui"]["height"]
		self.MainWindow.resize(width, height)
		self.MainWindow.set_position(gtk.WIN_POS_CENTER)
		self.MainWindow.show()
		self.minimized = False
		del config2
		self.clip = gtk.Clipboard(display=gtk.gdk.display_get_default(), selection="CLIPBOARD")
		self.roomlist = roomlist(self)
		
		self.logpopupmenu = PopupMenu(self).setup(
			("#" + _("Find"), self.OnFindLogWindow, gtk.STOCK_FIND),
			("#" + _("Copy"), self.OnCopyLogWindow, gtk.STOCK_COPY),
			("#" + _("Copy All"), self.OnCopyAllLogWindow, gtk.STOCK_COPY),
			("#" + _("Clear log"), self.OnClearLogWindow, gtk.STOCK_CLEAR)
		)
		def on_delete_event(widget, event):
			if self.HAVE_TRAYICON:
				option = QuitBox(self, title=_('Close Nicotine-Plus?'), message=_('Are you sure you wish to exit Nicotine-Plus at this time?'),tray=True, status="question", third=_("Send to tray") )
			else:
				option = QuitBox(self, title=_('Close Nicotine-Plus?'), message=_('Are you sure you wish to exit Nicotine-Plus at this time?'), tray=False, status="question" )
			
			return True

		self.MainWindow.connect("delete-event",on_delete_event)
		def window_state_event_cb(window, event):
			if event.changed_mask & gtk.gdk.WINDOW_STATE_ICONIFIED:
				if event.new_window_state & gtk.gdk.WINDOW_STATE_ICONIFIED:
					self.minimized = 1
				else:
					self.minimized = 0


		self.MainWindow.connect('window-state-event', window_state_event_cb)

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
		)
		self.LikesList.connect("button_press_event", self.OnPopupTILMenu)

		self.dislikes = {}
		self.dislikeslist = gtk.ListStore(gobject.TYPE_STRING)
		self.dislikeslist.set_sort_column_id(0, gtk.SORT_ASCENDING)
		cols = utils.InitialiseColumns(self.DislikesList, [_("I dislike")+":", 0, "text", self.CellDataFunc])
		cols[0].set_sort_column_id(0)
		self.DislikesList.set_model(self.dislikeslist)
		self.tidl_popup_menu = popup = utils.PopupMenu(self)
		popup.setup(("#" + _("Remove this item"), self.OnRemoveThingIDislike, gtk.STOCK_CANCEL))
		self.DislikesList.connect("button_press_event", self.OnPopupTIDLMenu)

		cols = utils.InitialiseColumns(self.RecommendationsList,
			[_("Recommendations"), 0, "text", self.CellDataFunc],
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

		self.status_context_id = self.Statusbar.get_context_id("")
		self.user_context_id = self.UserStatus.get_context_id("")
		self.down_context_id = self.DownStatus.get_context_id("")
		self.up_context_id = self.UpStatus.get_context_id("")

		self.MainWindow.connect("destroy", self.OnDestroy)
		self.MainWindow.connect("key_press_event", self.OnKeyPress)
		self.MainWindow.connect("motion-notify-event", self.OnButtonPress)
		
		gobject.signal_new("network_event", gtk.Window, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
		gobject.signal_new("network_event_lo", gtk.Window, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))
		self.MainWindow.connect("network_event", self.OnNetworkEvent)
		self.MainWindow.connect("network_event_lo", self.OnNetworkEvent)

		self.np = NetworkEventProcessor(self, self.callback, self.logMessage, self.SetStatusText, config)
		utils.DECIMALSEP = self.np.config.sections["ui"]["decimalsep"]
		utils.CATCH_URLS = self.np.config.sections["urls"]["urlcatching"]
		utils.HUMANIZE_URLS = self.np.config.sections["urls"]["humanizeurls"]
		utils.PROTOCOL_HANDLERS = self.np.config.sections["urls"]["protocols"].copy()
		utils.PROTOCOL_HANDLERS["slsk"] = self.OnSoulSeek
		utils.USERNAMEHOTSPOTS = self.np.config.sections["ui"]["usernamehotspots"]


		
		for thing in self.np.config.sections["interests"]["likes"]:
			self.likes[thing] = self.likeslist.append([thing])
		for thing in self.np.config.sections["interests"]["dislikes"]:
			self.dislikes[thing] = self.dislikeslist.append([thing])

		closers = self.np.config.sections["ui"]["tabclosers"]
		for w in self.ChatNotebook, self.PrivatechatNotebook, self.UserInfoNotebook, self.UserBrowseNotebook, self.SearchNotebook:
			w.tabclosers = closers
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
		self.LogWindow.show()
		self.LogScrolledWindow.add(self.LogWindow)
		self.LogWindow.connect("button-press-event", self.OnPopupLogMenu)
		
		

		if self.translux:
			self.LogScrolledWindow.get_vadjustment().connect("value-changed", lambda *args: self.LogWindow.queue_draw())
			self.translux.subscribe(self.LogWindow, lambda: self.LogWindow.get_window(gtk.TEXT_WINDOW_TEXT))
	        
		if self.np.config.sections["logging"]["logcollapsed"]:
			self.hide_log_window1.set_active(1)
		else:
			self.vpaned1.pack2(self.LogScrolledWindow, False, True)
			self.hide_log_window1.set_active(0)
		
		if self.np.config.sections["ui"]["roomlistcollapsed"]:
			self.hide_room_list1.set_active(1)
		else:
			self.vpaned3.pack2(self.roomlist.vbox2,True, True)
			self.hide_room_list1.set_active(0)
			
		self.userlistvbox = gtk.VBox(False, 0)
		self.userlistvbox.show()
		self.userlistvbox.set_spacing(0)
		self.userlistvbox.set_border_width(0)
	
		self.scrolledwindow11 = gtk.ScrolledWindow()
		self.scrolledwindow11.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.scrolledwindow11.show()
		self.scrolledwindow11.set_shadow_type(gtk.SHADOW_NONE)
	
		self.UserList = gtk.TreeView()
		self.UserList.show()
		self.UserList.set_headers_visible(True)
		self.scrolledwindow11.add(self.UserList)
	
		self.userlistvbox.pack_start(self.scrolledwindow11, True, True, 0)
	
		self.hbox3 = gtk.HBox(False, 3)
		self.hbox3.show()
		self.hbox3.set_spacing(5)
		self.hbox3.set_border_width(3)
		self.label12 = gtk.Label(_("Add Buddy: "))
		self.label12.set_padding(0, 0)
		self.label12.show()
		self.hbox3.pack_start(self.label12, False, False, 0)
	
		self.AddUserEntry = gtk.Entry()
		self.AddUserEntry.set_text("")
		self.AddUserEntry.set_editable(True)
		self.AddUserEntry.show()
		self.AddUserEntry.set_visibility(True)
		self.AddUserEntry.connect("activate", self.OnAddUser)
		self.hbox3.pack_start(self.AddUserEntry, True, True, 0)
	
		self.userlistvbox.pack_start(self.hbox3, False, True, 0)

		if int(self.np.config.sections["ui"]["buddylistinchatrooms"]):
			self.buddylist_in_chatrooms1.set_active(1)
		else:
			self.custom8 = self.get_custom_widget("custom8", _("ImageLabel"), _("Buddy list"), 0, 0)
			self.custom8.show()
			self.notebook1.append_page(self.userlistvbox, self.custom8)
			
			
		if self.np.config.sections["ticker"]["hide"]:
			self.hide_tickers1.set_active(1)
		self.UpdateColours(1)
		self.settingswindow = SettingsWindow(self)
		self.settingswindow.SettingsWindow.connect("settings-closed", self.OnSettingsClosed)
		
		self.chatrooms = ChatRooms(self)
		self.searches = Searches(self)
		self.downloads = Downloads(self)
		self.uploads = Uploads(self)
		self.userlist = UserList(self)

		self.privatechats = self.PrivatechatNotebook
		self.userinfo = self.UserInfoNotebook
		self.userbrowse = self.UserBrowseNotebook

		self.userinfo.SetTabLabel(self.UserInfoTabLabel)
		self.userbrowse.SetTabLabel(self.UserBrowseTabLabel)
		
		self.sUserinfoButton.connect("clicked", self.OnGetUserInfo)
		self.UserinfoEntry.connect("activate", self.OnGetUserInfo)
		
		self.sPrivateChatButton.connect("clicked", self.OnGetPrivateChat)
		self.PrivateChatEntry.connect("activate", self.OnGetPrivateChat)
		
		self.sSharesButton.connect("clicked", self.OnGetShares)
		self.SharesEntry.connect("activate", self.OnGetShares)
		
		
		self.SetUserStatus(_("Offline"))
		self.UpdateBandwidth()
		self.UpdateTransferButtons()
		
		self.disconnect1.set_sensitive(0)
		self.awayreturn1.set_sensitive(0)
		self.check_privileges1.set_sensitive(0)
		self.current_image=None
		self.tray_status = {"hilites" : { "rooms": [], "private": [] }, "status": "disconnect", "last": "disconnect"}
		if self.CREATE_TRAYICON:
			self.create_trayicon()
		if self.HAVE_TRAYICON:
			self.draw_trayicon()
		if self.np.config.sections["transfers"]["rescanonstartup"]:
			self.OnRescan()
		img = gtk.Image()
		img.set_from_pixbuf(self.images["away2"])
		self.awayreturn1.set_image(img)
		self.now = nowplaying.NowPlaying(self)
		if self.np.config.needConfig():
			self.connect1.set_sensitive(0)
			self.rescan1.set_sensitive(0)
			self.logMessage(_("You need to configure your settings (Server, Username, Password, Download Directory) before connecting..."))
			self.OnSettings(None)
		else:
			self.OnConnect(-1)
		self.UpdateDownloadFilters()
		
	def importimages(self):
		try:
			import imagedata

		except Exception, e:
			print e
			
	def create_trayicon(self):
		if self.TRAYICON_FAILED:
			return
		if sys.platform == "win32":
			try:
			
				import systraywin32
				self.trayicon_module = systraywin32
			except ImportError, error:
				self.TRAYICON_FAILED = True
				self.HAVE_TRAYICON = False
				message =  _("Note: The systraywin32.py Python file failed to load properly because: %s. You may require pywin32. Get a version that matches your version of Python from here:\nhttp://sourceforge.net/project/showfiles.php?group_id=78018") % error
				print message
				self.logMessage(message, "TrayIcon")
		else:
			# PyGTK >= 2.10
			if gtk.pygtk_version[0] >= 2 and gtk.pygtk_version[1] >= 10:
				trayicon = gtk.StatusIcon()
				self.trayicon_module = trayicon
				self.HAVE_TRAYICON = True
				self.TRAYICON_FAILED = False
			else:
			        try:
					from pynicotine import trayicon
			        	self.trayicon_module = trayicon
					self.HAVE_TRAYICON = True
					self.TRAYICON_FAILED = False
				except:
					self.TRAYICON_FAILED = True
					self.HAVE_TRAYICON = False
					message = _("Note: Trayicon Python module was not found in the pynicotine directory: %s") % error
					print message
					self.logMessage(message, "TrayIcon")
			
	def destroy_trayicon(self):
		if not self.TRAYICON_CREATED:
			return
		self.TRAYICON_CREATED = 0
		self.HAVE_TRAYICON = 0
		self.current_image = None
		
		if sys.platform != "win32":
			if gtk.pygtk_version[0] >= 2 and gtk.pygtk_version[1] >= 10:
				self.trayicon_module.set_visible(False)
				self.trayicon_module = None
			else:
				self.eventbox.destroy()
				self.trayicon.destroy()
		else:
			self.tray_status["last"] = ""
			self.trayicon.hide_icon()
		
		self.tray_popup_menu.destroy()

		
	def draw_trayicon(self):
		if not self.HAVE_TRAYICON or self.trayicon_module == None or self.TRAYICON_CREATED:
			return
		self.TRAYICON_CREATED = 1
		self.is_mapped = 1
		self.traymenu()
		if sys.platform == "win32":
			if not self.trayicon:
				self.trayicon = self.trayicon_module.TrayIcon("Nicotine", self)
			self.trayicon.show_icon()
			
		else:
			if gtk.pygtk_version[0] >= 2 and gtk.pygtk_version[1] >= 10:
				self.trayicon_module.set_visible(True)
				self.trayicon_module.connect("popup-menu", self.OnStatusIconPopup)
				self.trayicon_module.connect("activate", self.OnStatusIconClicked)
			else:
				self.trayicon = self.trayicon_module.TrayIcon("Nicotine")
				self.eventbox = gtk.EventBox()
				self.trayicon.add(self.eventbox)
				self.eventbox.connect("button-press-event", self.OnTrayiconClicked)
				self.trayicon.show_all()
	
			
		self.load_image(self.tray_status["status"])

				
		
	def Notification(self, location, user, room=None):
		hilites = self.tray_status["hilites"]
		if location == "rooms" and room != None and user != None:
			if room not in hilites["rooms"]:
				hilites["rooms"].append(room)
				self.sound("room_nick", user, place=room)
				self.load_image()
				#self.MainWindow.set_urgency_hint(True)
		if location == "private":
			if user in hilites[location]:
				hilites[location].remove(user)
				hilites[location].append(user)
			if user not in hilites[location]: 
				hilites[location].append(user)
				self.sound(location, user)
				self.load_image()
				#self.MainWindow.set_urgency_hint(True)
		self.TitleNotification(user)
		
	def ClearNotification(self, location, user, room=None):
		if location == "rooms" and room != None:
			if room in self.tray_status["hilites"]["rooms"]:
				self.tray_status["hilites"]["rooms"].remove(room)
		if location == "private":	
			if user in self.tray_status["hilites"]["private"]: 
				self.tray_status["hilites"]["private"].remove(user)
		self.TitleNotification(user)
		self.load_image()
		
	def TitleNotification(self, user=None):
		if self.tray_status["hilites"]["rooms"] == [] and self.tray_status["hilites"]["private"] == []:
			# Reset Title
			if self.MainWindow.get_title() != _("Nicotine+") + " " + version:  
				self.MainWindow.set_title(_("Nicotine+") + " " + version)
		else:
			# Private Chats have a higher priority
			if len(self.tray_status["hilites"]["private"]) > 0:
				user = self.tray_status["hilites"]["private"][-1]
				self.MainWindow.set_title(_("Nicotine+") + " " + version+ " :: " +  _("Private Message from %(user)s" % {'user':user} ) )
			# Allow for the possibility the username is not available
			elif len(self.tray_status["hilites"]["rooms"]) > 0:
				room = self.tray_status["hilites"]["rooms"][-1]
				if user == None:
					self.MainWindow.set_title(_("Nicotine+") + " " + version+ " :: " +  _("You've been mentioned in the %(room)s room" % {'room':room} ) )
				else:
					self.MainWindow.set_title(_("Nicotine+") + " " + version+ " :: " +  _("%(user)s mentioned you in the %(room)s room" % {'user':user, 'room':room } ) )
				
	def load_image(self, status=None):
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

			if sys.platform == "win32":
				# For Win32 Systray 
				self.trayicon.set_img(icon)
			else:
				if gtk.pygtk_version[0] >= 2 and gtk.pygtk_version[1] >= 10:
					self.trayicon_module.set_from_pixbuf(self.images[icon])
				else:
					# For trayicon.so module X11 Systray 
					self.eventbox.hide()
					if self.current_image != None:
						self.eventbox.remove(self.current_image)
				
					img = gtk.Image()
					img.set_from_pixbuf(self.images[icon])
					img.show()
	
					self.current_image = img
					self.eventbox.add(self.current_image)
					self.eventbox.show()
		except Exception,e:
			print "ERROR: load_image", e
			
	def sound(self, message, user, place=None):
		if sys.platform == "win32":
			return
		if "soundenabled" in self.np.config.sections["ui"]:
			if not self.np.config.sections["ui"]["soundenabled"]:
				return
		else: return
		if "speechenabled" in self.np.config.sections["ui"]:
			if self.np.config.sections["ui"]["speechenabled"]:
				if message == "room_nick" and place is not None:
					os.system("flite -t \"%s, the user, %s has mentioned your name in the room, %s.\" &" %(self.np.config.sections[ "server"]["login"], user, place) )
				elif message == "private":
					os.system("flite -t \"%s, you have recieved a private message from %s.\" &" %(self.np.config.sections["server"]["login"], user ) )
				return
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
			if "soundcommand" in self.np.config.sections["ui"]:
				os.system("%s %s &" % ( self.np.config.sections["ui"]["soundcommand"], path))
	
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
			if sys.platform == "win32" and self.trayicon:
				self.trayicon.hide_icon()
			self.MainWindow.destroy()
			gtk.main_quit()
			
		elif response == gtk.RESPONSE_CANCEL:
			pass
			
		elif response == gtk.RESPONSE_REJECT:
			
			if self.is_mapped:
				self.MainWindow.unmap()
				self.is_mapped = 0

	
			
	def OnGetUserInfo(self, widget):
		text = self.UserinfoEntry.get_text()
		if not text:
			return
		self.LocalUserInfoRequest(text)
		self.UserinfoEntry.set_text("")
		
	def OnGetShares(self, widget):
		text = self.SharesEntry.get_text()
		if not text:
			return
		self.BrowseUser(text)
		self.SharesEntry.set_text("")
	
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
		
		
	def OnGetPrivateChat(self, widget):
		text = self.PrivateChatEntry.get_text()
		if not text:
			return
		self.privatechats.SendMessage(text, None, 1)
		self.PrivateChatEntry.set_text("")
		
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
# 			self.np.ProcessRequestToPeer(user, slskmessages.UserInfoRequest(None), self.userinfo)
			
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
			
	def traymenu(self):
		try:

			self.tray_popup_menu_server = popup0 = PopupMenu(self)
			popup0.setup(
				("#" + _("Connect"), self.OnConnect, gtk.STOCK_CONNECT),
				("#" + _("Disconnect"), self.OnDisconnect, gtk.STOCK_DISCONNECT),
			)
			self.tray_popup_menu = popup = PopupMenu(self)
			popup.setup(
				("#" + _("Hide / Unhide Nicotine"), self.HideUnhideWindow, gtk.STOCK_GOTO_BOTTOM),
				(1, _("Server"), self.tray_popup_menu_server, self.OnPopupServer),
				("#" + _("Settings"), self.OnSettings, gtk.STOCK_PREFERENCES),
				("#" + _("Lookup a User's IP"), self.OnGetAUsersIP, gtk.STOCK_NETWORK),
				("#" + _("Lookup a User's Info"), self.OnGetAUsersInfo, gtk.STOCK_DIALOG_INFO),
				("#" + _("Lookup a User's Shares"), self.OnGetAUsersShares, gtk.STOCK_HARDDISK),
				("%" + _("Toggle Away"), self.OnAway, self.images["away2"] ),
				("#" + _("Quit"), self.OnExit, gtk.STOCK_QUIT),
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
			
	def HideUnhideWindow(self, widget):
		if self.is_mapped:
			self.MainWindow.unmap()
			self.is_mapped = 0
		else:
						
			self.MainWindow.map()
			# weird, but this allows us to easily a minimized nicotine from one
			# desktop to another by clicking on the tray icon
			if self.minimized:
				self.MainWindow.present()
			self.MainWindow.grab_focus()
			self.is_mapped = 1
			
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
				items[3].set_sensitive(False)
				items[4].set_sensitive(False)
				items[5].set_sensitive(False)
				items[6].set_sensitive(False)
			else:
				
				items[3].set_sensitive(True)
				items[4].set_sensitive(True)
				items[5].set_sensitive(True)
				items[6].set_sensitive(True)
			if event.type == gtk.gdk.BUTTON_PRESS:
				self.tray_popup_menu.popup(None, None, None, event.button, event.time)
				return True
			return False
				
	def get_custom_widget(self, id, string1, string2, int1, int2):
		if id in ["ChatNotebook", "SearchNotebook"]:
			return IconNotebook(self.images)
		elif id == "PrivatechatNotebook":
			return PrivateChats(self)
		elif id == "UserInfoNotebook":
			return UserTabs(self, UserInfo)
		elif id == "UserBrowseNotebook":
			return UserTabs(self, UserBrowse)
		elif string1 == "ImageLabel":
			return ImageLabel(string2, self.images["empty"])
		else:
			return MainWindow.get_custom_widget(self, id, string1, string2, int1, int2)

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
				self.notebook1.set_current_page(i-1)
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
			if self.np.events.has_key(i.__class__):
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
		if self.frame.np.config.sections["ui"].has_key(colour):
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
		self.SetTextBG(self.RecommendationUsersList)
		self.SetTextBG(self.LikesList)
		self.SetTextBG(self.DislikesList)
		self.SetTextBG(self.PrivateChatEntry)
		self.SetTextBG(self.UserinfoEntry)
		self.SetTextBG(self.SharesEntry)
		self.SetTextBG(self.AddUserEntry)
		self.SetTextBG(self.SearchEntry)
		
		
	def SetTextBG(self, widget):
		bgcolor = self.np.config.sections["ui"]["textbg"]
		if bgcolor == "":
			colour = None
		else:
			colour = gtk.gdk.color_parse(bgcolor)
			
		widget.modify_base(gtk.STATE_NORMAL, colour)
		widget.modify_bg(gtk.STATE_NORMAL, colour)
		
		if type(widget) is gtk.Entry:
			fgcolor = self.np.config.sections["ui"]["inputcolor"]
			if fgcolor == "":
				colour = None
			else:
				colour = gtk.gdk.color_parse(fgcolor)
			widget.modify_text(gtk.STATE_NORMAL, colour)
			widget.modify_fg(gtk.STATE_NORMAL, colour)
			
	def logMessage(self, msg, debug = None):
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
		self.np.StopTimers()
		if self.np.transfers is not None:
	            self.np.transfers.AbortTransfers()
		    
		self.np.config.sections["privatechat"]["users"] = self.privatechats.users.keys()
			
		self.np.config.writeConfig()
		self.np.protothread.abort()
		if sys.platform == "win32":
			if self.trayicon:
				self.trayicon.hide_icon()
		gtk.main_quit()
		
	def OnConnect(self, widget):
		self.connect1.set_sensitive(0)
		self.disconnect1.set_sensitive(1)
		self.tray_status["status"] = "connect"
		self.load_image()
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
			self.np.queue.put(slskmessages.GetUserStatus(user[0]))
			self.np.queue.put(slskmessages.GetUserStats(user[0]))
		return False
		
	def ConnClose(self, conn, addr):
		if self.awaytimer is not None:
			gobject.source_remove(self.awaytimer)
			self.awaytimer = None
		if self.autoaway:
			self.autoaway = self.away = False
		
		self.connect1.set_sensitive(1)
		self.disconnect1.set_sensitive(0)
		self.awayreturn1.set_sensitive(0)
		self.check_privileges1.set_sensitive(0)
		
		self.SetUserStatus(_("Offline"))
		self.tray_status["status"] = "disconnect"
		self.load_image()
		self.searches.interval = 0
		self.chatrooms.ConnClose()
		self.privatechats.ConnClose()
		self.searches.ConnClose()
		self.uploads.ConnClose()
		self.downloads.ConnClose()
		self.userlist.ConnClose()
	
	def ConnectError(self, conn):
		self.connect1.set_sensitive(1)
		self.disconnect1.set_sensitive(0)
		
		self.SetUserStatus(_("Offline"))
		self.tray_status["status"] = "disconnect"
		self.load_image()
		
	def SetUserStatus(self, status):
		self.UserStatus.pop(self.user_context_id)
		self.UserStatus.push(self.user_context_id, status)
		
	def InitInterface(self, msg):
		if self.away == 0:
			self.SetUserStatus(_("Online"))
			self.tray_status["status"] = "connect"
			self.load_image()
			autoaway = self.np.config.sections["server"]["autoaway"]
			if autoaway > 0:
				self.awaytimer = gobject.timeout_add(1000*60*autoaway, self.OnAutoAway)
			else:
				self.awaytimer = None
		else:
			self.SetUserStatus(_("Away"))
			self.tray_status["status"] = "away2"
			self.load_image()
		
		self.awayreturn1.set_sensitive(1)
		self.check_privileges1.set_sensitive(1)
		
		self.uploads.InitInterface(self.np.transfers.uploads)
		self.downloads.InitInterface(self.np.transfers.downloads)
		gobject.idle_add(self.FetchUserListStatus)
		
		AppendLine(self.LogWindow, self.np.decode(msg.banner), self.tag_log)
		return self.privatechats, self.chatrooms, self.userinfo, self.userbrowse, self.searches, self.downloads, self.uploads, self.userlist

	def GetStatusImage(self, status):
		if status == 1:
			return self.images["away"]
		elif status == 2:
			return self.images["online"]
		else:
			return self.images["offline"]
	
	def OnShowDebug(self, widget):
		self.showdebug = widget.get_active()

	def OnAway(self, widget):
		self.away = (self.away+1) % 2
		if self.away == 0:
			self.SetUserStatus(_("Online"))
			self.tray_status["status"] = "connect"
			self.load_image()
		else:
			self.SetUserStatus(_("Away"))
			self.tray_status["status"] = "away2"
			self.load_image()
		self.np.queue.put(slskmessages.SetStatus(self.away and 1 or 2))

		
	def OnExit(self, widget):
		
		self.MainWindow.destroy()
	
	def OnSearch(self, widget):
		self.searches.OnSearch()
		
	def OnClearSearchHistory(self, widget):
		self.searches.OnClearSearchHistory()
		
	def ChatRequestIcon(self, status = 0):
		if status == 1 and not self.got_focus:
			self.MainWindow.set_icon(self.images["hilite2"])
		if self.notebook1.get_current_page() == 0:
			return
		if status == 0:
			if self.ChatTabLabel.get_image() == self.images["hilite"]:
				return
		self.ChatTabLabel.set_image(status == 1 and self.images["hilite"] or self.images["online"])

	def RequestIcon(self, tablabel):
		if tablabel == self.PrivateChatTabLabel and not self.got_focus:
			self.MainWindow.set_icon(self.images["hilite2"])
		if self.current_tab != tablabel:
			tablabel.set_image(self.images["hilite"])
			
		
	def OnSwitchPage(self, notebook, page, page_nr):
		l = [self.ChatTabLabel, self.PrivateChatTabLabel, None, None, self.SearchTabLabel, self.UserInfoTabLabel, self.UserBrowseTabLabel, None, None][page_nr]
		n = [self.ChatNotebook, self.PrivatechatNotebook, None, None, self.SearchNotebook, self.UserInfoNotebook, self.UserBrowseNotebook, None, None][page_nr]
		self.current_tab = l
		if l is not None:
			l.set_image(self.images["empty"])
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

		if self.np.transfers is not None:
			usersdown, down = _calc(self.np.transfers.downloads)
			usersup, up = _calc(self.np.transfers.uploads)
		else:
			down = up = 0.0
			usersdown = usersup = 0
		
		self.DownStatus.pop(self.down_context_id)
		self.UpStatus.pop(self.up_context_id)
		self.DownStatus.push(self.down_context_id, _("Down: %(num)i users, %(speed).1f KB/s") % {'num':usersdown, 'speed':down})
		self.UpStatus.push(self.up_context_id, _("Up: %(num)i users, %(speed).1f KB/s") % {'num':usersup,'speed':up})
	
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

		
	def OnRescan(self, widget = None):
		if self.rescanning:
			return
		self.rescanning = 1
		
		self.rescan1.set_sensitive(False)
		self.logMessage(_("Rescanning started"))
		
		shared = self.np.config.sections["transfers"]["shared"][:]
		if self.np.config.sections["transfers"]["sharedownloaddir"]:
			shared.append(self.np.config.sections["transfers"]["downloaddir"])
		cleanedshares = []
		for i in shared:
			if i not in cleanedshares:
				cleanedshares.append(i)
		msg = slskmessages.RescanShares(cleanedshares, lambda: None)
		thread.start_new_thread(self.np.RescanShares, (msg,))
		
		
	def OnBuddyRescan(self, widget = None):
		if self.brescanning:
			return
		self.brescanning = 1
		
		self.rescan2.set_sensitive(False)
		self.logMessage(_("Rescanning Buddy Shares started"))
		
		shared = self.np.config.sections["transfers"]["buddyshared"][:] + self.np.config.sections["transfers"]["shared"][:]
		if self.np.config.sections["transfers"]["sharedownloaddir"]:
			shared.append(self.np.config.sections["transfers"]["downloaddir"])
		cleanedshares = []
		for i in shared:
			if i not in cleanedshares:
				cleanedshares.append(i)
		msg = slskmessages.RescanBuddyShares(cleanedshares, lambda: None)
		thread.start_new_thread(self.np.RescanBuddyShares, (msg,))
		
	def _BuddyRescanFinished(self, data):
		self.np.config.setBuddyShares(*data)
		self.np.config.writeShares()
		
		self.rescan2.set_sensitive(True)
		if self.np.transfers is not None:
			self.np.sendNumSharedFoldersFiles()
		self.brescanning = 0
		self.logMessage(_("Rescanning Buddy Shares finished"))
		self.BuddySharesProgress.hide()
		
	def _RescanFinished(self, data):
		self.np.config.setShares(*data)
		self.np.config.writeShares()
		
		self.rescan1.set_sensitive(True)
		if self.np.transfers is not None:
			self.np.sendNumSharedFoldersFiles()
		self.rescanning = 0
		self.logMessage(_("Rescanning finished"))
		self.SharesProgress.hide()
		
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
			return
		
		needrescan, needcolors, config = self.settingswindow.GetSettings()
		for (key, data) in config.items():
			self.np.config.sections[key].update(data)
		
		utils.DECIMALSEP = self.np.config.sections["ui"]["decimalsep"]
		utils.CATCH_URLS = self.np.config.sections["urls"]["urlcatching"]
		utils.HUMANIZE_URLS = self.np.config.sections["urls"]["humanizeurls"]
		utils.PROTOCOL_HANDLERS = self.np.config.sections["urls"]["protocols"].copy()
		utils.PROTOCOL_HANDLERS["slsk"] = self.OnSoulSeek
		utils.USERNAMEHOTSPOTS = self.np.config.sections["ui"]["usernamehotspots"]
		uselimit = self.np.config.sections["transfers"]["uselimit"]
		uploadlimit = self.np.config.sections["transfers"]["uploadlimit"]
		limitby = self.np.config.sections["transfers"]["limitby"]
		if self.np.config.sections["transfers"]["geoblock"]:
			panic = self.np.config.sections["transfers"]["geopanic"]
			cc = self.np.config.sections["transfers"]["geoblockcc"]
			self.np.queue.put(slskmessages.SetGeoBlock([panic, cc]))
		else:
			self.np.queue.put(slskmessages.SetGeoBlock(None))
		self.np.queue.put(slskmessages.SetUploadLimit(uselimit,uploadlimit,limitby))
		self.UpdateDownloadFilters()
		self.TransparentTint(1)
		self.np.config.writeConfig()
		if not self.np.config.sections["ui"]["trayicon"] and self.HAVE_TRAYICON:
			self.destroy_trayicon()
		elif self.np.config.sections["ui"]["trayicon"] and not self.HAVE_TRAYICON:
			if self.trayicon_module == None and not self.TRAYICON_CREATED:
				self.create_trayicon()
			else:
				self.HAVE_TRAYICON = 1
				
			self.draw_trayicon()
			
		if needcolors:
			self.chatrooms.roomsctrl.UpdateColours()
			self.privatechats.UpdateColours()
			self.searches.UpdateColours()
			self.downloads.UpdateColours()
			self.uploads.UpdateColours()
			self.userinfo.UpdateColours()
			self.userbrowse.UpdateColours()
			
			self.UpdateColours()
			
		if self.np.transfers is not None:
			self.np.transfers.checkUploadQueue()
		self.UpdateTransferButtons()
		if needrescan:
			self.needrescan = 1
		
		if msg == "ok" and self.needrescan:
			self.needrescan = 0
			self.BothRescan()


		if self.np.config.needConfig():
			self.connect1.set_sensitive(0)
			self.logMessage(_("You need to finish configuring your settings (Server, Username, Password, Download Directory) before connecting... but if this message persists, check your Nicotine config file for options set to \'None\'."))
		else:
			if self.np.transfers is None:
				self.connect1.set_sensitive(1)

	def TransparentTint(self, update=None):

		if not self.np.config.sections["ui"]["enabletrans"]:
			if self.translux:
				self.translux.disable()
			return
	
		filter =""
		tint = None
		ttint = self.np.config.sections["ui"]["transtint"]
		if ttint[0] != "#":
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
		file = "doc/NicotinePlusGuide.html" 
		if os.path.exists(file):
			url = "file://%s/%s" % (os.environ["PWD"], file)
			self.OpenUrl(url)
		else:
			file = "%s/share/nicotine/documentation/NicotinePlusGuide.html" % sys.prefix
			if os.path.exists(file):
				url = "file://%s" % file
				self.OpenUrl(url)
			else:
				popupWarning(None, _("Cannot Find Guide"), _("The Nicotine Offline Guide ( NicotinePlusGuide.html ) was not found in either the following directories:\n\n<u>%(pwd)s/doc/\n</u><b>and</b>\n<u>%(prefix)s/share/nicotine/documentation/</u>\n\nEither install Nicotine-Plus, or start from inside the Nicotine-Plus source directory." % {'pwd':os.environ["PWD"], 'prefix':sys.prefix } ) )
		
	def OnSourceForgeProject(self, widget):
		url = "http://sourceforge.net/projects/nicotine-plus/"
		self.OpenUrl(url)
		
	def OnTrac(self, widget):
		url = "http://nicotine-plus.org/"
		self.OpenUrl(url)
		
	def OpenUrl(self, url):
		if utils.PROTOCOL_HANDLERS.has_key("http"):
			if utils.PROTOCOL_HANDLERS["http"].__class__ is utils.types.MethodType:
				utils.PROTOCOL_HANDLERS["http"](url)
			else:
				cmd = utils.PROTOCOL_HANDLERS["http"] % url
				os.system(cmd)
		else:
			try:
				import gnome.vfs
				gnome.url_show(url)
			except Exception, e:
				pass
	def OnAbout(self, widget):
		dlg = AboutDialog(self.MainWindow)
		dlg.run()
		dlg.destroy()

	def OnAboutChatroomCommands(self, widget):
		dlg = AboutRoomsDialog(self.MainWindow)
		dlg.run()
		dlg.destroy()
	
	def OnAboutPrivateChatCommands(self, widget):
		dlg = AboutPrivateDialog(self.MainWindow)
		dlg.run()
		dlg.destroy()
	
	def OnAboutFilters(self, widget):
		dlg = AboutFiltersDialog(self.MainWindow)
		dlg.run()
		dlg.destroy()

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
			if self.userlistvbox in self.notebook1.get_children():
				self.notebook1.remove_page(8)
			if self.userlistvbox not in self.vpaned3.get_children():
				self.vpaned3.pack1(self.userlistvbox, True, True)
		else:
			if self.hide_room_list1.get_active():
				self.vpaned3.hide()
			if self.userlistvbox in self.vpaned3.get_children():
				self.vpaned3.remove(self.userlistvbox)
			self.custom8 = self.get_custom_widget("custom8", _("ImageLabel"), _("Buddy list"), 0, 0)
			self.custom8.show()
			if self.userlistvbox not in self.notebook1.get_children():
				self.notebook1.append_page(self.userlistvbox, self.custom8)
       			
			
		
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
				m = slskmessages.SharedFileList(None,self.np.config.sections["transfers"]["bsharedfilesstreams"])
			else:
				m = slskmessages.SharedFileList(None,self.np.config.sections["transfers"]["sharedfilesstreams"])
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

	def OnPopupLogMenu(self, widget, event):
		if event.button != 3:
			return False
		widget.emit_stop_by_name("button-press-event")
		self.logpopupmenu.popup(None, None, None, event.button, event.time)
		return True
	
	def OnFindLogWindow(self, widget):

		self.OnFindTextview(widget, self.LogWindow)
				
	def OnFindTextview(self, widget, textview):

		if not self.__dict__.has_key("FindDialog"):
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
			if rating >= 100000 :
				rating = 0
			thing = self.np.decode(thing)
			self.recommendationslist.append([thing, Humanize(rating), rating])
		self.recommendationslist.set_sort_column_id(2, gtk.SORT_DESCENDING)

	def GlobalRecommendations(self, msg):
		self.SetRecommendations("Global recommendations", msg.recommendations)

	def Recommendations(self, msg):
		self.SetRecommendations("Recommendations", msg.recommendations)

	def ItemRecommendations(self, msg):
		self.SetRecommendations(_("Recommendations for %s") % msg.thing, msg.recommendations)

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
			self.np.queue.put(slskmessages.GetUserStats(user))
			self.np.queue.put(slskmessages.GetUserStatus(user))

	def ItemSimilarUsers(self, msg):
		self.recommendationuserslist.clear()
		self.recommendationusers = {}
		for user in msg.users:
			iter = self.recommendationuserslist.append([self.images["offline"], user, "0", "0", 0, 0, 0])
			self.recommendationusers[user] = iter
			self.np.queue.put(slskmessages.AddUser(user))
			self.np.queue.put(slskmessages.GetUserStats(user))
			self.np.queue.put(slskmessages.GetUserStatus(user))

	def GetUserStatus(self, msg):
		if not self.recommendationusers.has_key(msg.user):
			return
		img = self.GetStatusImage(msg.status)
		self.recommendationuserslist.set(self.recommendationusers[msg.user], 0, img, 4, msg.status)

	def GetUserStats(self, msg):
		if not self.recommendationusers.has_key(msg.user):
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
				self.notebook1.set_current_page(1)
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
		thing = self.r_popup_menu.get_user()
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
		thing = self.r_popup_menu.get_user()
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
		thing = self.r_popup_menu.get_user()
		self.SearchEntry.set_text(thing)
		self.notebook1.set_current_page(4)

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

	def OnHideTickers(self, widget):
		if not self.chatrooms:
			return
		hide = widget.get_active()
		self.np.config.sections["ticker"]["hide"] = hide
		self.np.config.writeConfig()
		for room in self.chatrooms.roomsctrl.joinedrooms.values():
			room.ShowTicker(not hide)
	
	def GivePrivileges(self, user, days):
		self.np.queue.put(slskmessages.GivePrivileges(user, days))
		
	def OnChatRooms(self, widget):
		self.notebook1.set_current_page(0)
	
	def OnPrivateChat(self, widget):
		self.notebook1.set_current_page(1)
	
	def OnDownloads(self, widget):
		self.notebook1.set_current_page(2)
	
	def OnUploads(self, widget):
		self.notebook1.set_current_page(3)
	
	def OnSearchFiles(self, widget):
		self.notebook1.set_current_page(4)
	
	def OnUserInfo(self, widget):
		self.notebook1.set_current_page(5)
	
	def OnUserBrowse(self, widget):
		self.notebook1.set_current_page(6)
	
	def OnInterests(self, widget):
		self.notebook1.set_current_page(7)
	
	def OnUserList(self, widget):
		self.notebook1.set_current_page(8)
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
