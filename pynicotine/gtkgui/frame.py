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
from utils import AppendLine, ImageLabel, IconNotebook, ScrollBottom, PopupMenu, Humanize
import translux

from pynicotine.utils import _

from entrydialog import  *
try:
	from pynicotine import trayicon
	HAVE_TRAYICON = 1
except ImportError, e:
	print e
	HAVE_TRAYICON = 0
	print "Warning: Trayicon Python module not found."

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

class testwin(MainWindow):
	def __init__(self, config):
		self.images = {}
		self.clip_data = ""
		self.configfile = config
		
		
		self.chatrooms = None
		
		self.got_focus = False
		config2 = Config(config)
        	config2.readConfig()
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
		del data
		del config2
		
		MainWindow.__init__(self)
		self.MainWindow.set_title(_("Nicotine+") + " " + version)
		self.MainWindow.set_icon(self.images["n"])
		self.MainWindow.selection_add_target("PRIMARY", "STRING", 1)
		self.MainWindow.set_geometry_hints(None, min_width=500, min_height=500)
		self.clip = gtk.Clipboard(display=gtk.gdk.display_get_default(), selection="CLIPBOARD")
		self.roomlist = roomlist(self)
		
		self.logpopupmenu = PopupMenu(self).setup([_("Clear log"), self.OnClearLogWindow])
		
		
		self.importimages()
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
		cols = utils.InitialiseColumns(self.LikesList, [_("I like")+":", 0, "text"])
		cols[0].set_sort_column_id(0)
		self.LikesList.set_model(self.likeslist)
		self.til_popup_menu = popup = utils.PopupMenu(self)
		popup.setup(
			(_("_Remove this item"), self.OnRemoveThingILike),
			(_("Re_commendations for this item"), self.OnRecommendItem),
		)
		self.LikesList.connect("button_press_event", self.OnPopupTILMenu)

		self.dislikes = {}
		self.dislikeslist = gtk.ListStore(gobject.TYPE_STRING)
		self.dislikeslist.set_sort_column_id(0, gtk.SORT_ASCENDING)
		cols = utils.InitialiseColumns(self.DislikesList, [_("I dislike")+":", 0, "text"])
		cols[0].set_sort_column_id(0)
		self.DislikesList.set_model(self.dislikeslist)
		self.tidl_popup_menu = popup = utils.PopupMenu(self)
		popup.setup((_("Remove this item"), self.OnRemoveThingIDislike))
		self.DislikesList.connect("button_press_event", self.OnPopupTIDLMenu)

		cols = utils.InitialiseColumns(self.RecommendationsList,
			[_("Recommendations"), 0, "text"],
			[_("Rating"), 75, "text"])
		cols[0].set_sort_column_id(0)
		cols[1].set_sort_column_id(2)
		self.recommendationslist = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT)
		self.RecommendationsList.set_model(self.recommendationslist)
		self.r_popup_menu = popup = utils.PopupMenu(self)
		popup.setup(
			("$" + _("I _like this"), self.OnLikeRecommendation),
			("$" + _("I _don't like this"), self.OnDislikeRecommendation),
			(_("_Recommendations for this item"), self.OnRecommendRecommendation),
			("", None),
			(_("_Search for this item"), self.OnRecommendSearch),
		)
		self.RecommendationsList.connect("button_press_event", self.OnPopupRMenu)

		cols = utils.InitialiseColumns(self.RecommendationUsersList, 
			["", -1, "pixbuf"],
			[_("User"), 100, "text"],
			[_("Speed"), 0, "text"],
			[_("Files"), 0, "text"],
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
			(_("Send _message"), popup.OnSendMessage),
			("", None),
			(_("Show IP a_ddress"), popup.OnShowIPaddress),
			(_("Get user i_nfo"), popup.OnGetUserInfo),
			(_("Brow_se files"), popup.OnBrowseUser),
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


		
		for thing in self.np.config.sections["interests"]["likes"]:
			self.likes[thing] = self.likeslist.append([thing])
		for thing in self.np.config.sections["interests"]["dislikes"]:
			self.dislikes[thing] = self.dislikeslist.append([thing])

		closers = self.np.config.sections["ui"]["tabclosers"]
		for w in self.ChatNotebook, self.PrivatechatNotebook, self.UserInfoNotebook, self.UserBrowseNotebook, self.SearchNotebook:
			w.tabclosers = closers
		
		if self.np.config.sections["ui"].has_key("filter"):
			self.translux = translux.Translux(self.MainWindow, eval(self.np.config.sections["ui"]["filter"]))
		else:
			self.translux = None

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
		self.UpdateColours()
		

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
	
		self.hbox3 = gtk.HBox(False, 0)
		self.hbox3.show()
		self.hbox3.set_spacing(0)
	
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
		self.tray_status = {"hilites" : { "rooms": [], "private": [] }, "status": "", "last": ""}
		if HAVE_TRAYICON:
			self.create_trayicon()
		if self.np.config.sections["transfers"]["rescanonstartup"]:
			self.OnRescan()

		if self.np.config.needConfig():
			self.connect1.set_sensitive(0)
			self.rescan1.set_sensitive(0)
			self.logMessage(_("You need to configure your settings (Server, Username, Password, Download Directory) before connecting..."))
			self.OnSettings(None)
		else:
			self.OnConnect(-1)
		
	def importimages(self):
		try:
			import imagedata
		except Exception, e:
			print e
		
	def create_trayicon(self):
		self.is_mapped = 1
		self.trayicon = trayicon.TrayIcon("Nicotine")
		
		self.eventbox = gtk.EventBox()
		img = gtk.Image()
		self.traymenu()
		self.load_image(None, "disconnect")

		self.trayicon.add(self.eventbox)
		self.trayicon.show_all()
		self.eventbox.connect("button-press-event", self.OnTrayiconClicked)
			
	def load_image(self, image, status=None):
		try:
			self.load_image_wrapped(image, status)
		except:
			print "Error changing Trayicon's icon, attempting to recreate it."
			try:
				self.create_trayicon()
			except:
				print "Trayicon failed to load"
				
	def load_image_wrapped(self, image, status=None):
	
		try:
			# Abort if Trayicon module wasn't loaded
			if not HAVE_TRAYICON:
				return
			if status != None:
				self.tray_status["status"] = status
			# Check for hilites, and display hilite icon if there is a room or private hilite
			if self.tray_status["hilites"]["rooms"] == [] and self.tray_status["hilites"]["private"] == []:
				icon = image
			else:
				icon = "hilite2"
			if icon == None:
				# If there is no hilite, display the status
				icon = self.tray_status["status"]
			if icon != self.tray_status["last"]:
				self.tray_status["last"] = icon
			else:
				# If the icon hasn't changed since the last time, do nothing
				return
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
			print "ERROR: load_image_wrapped", e
	
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

	def OnGetPrivateChat(self, widget):
		text = self.PrivateChatEntry.get_text()
		if not text:
			return
		self.privatechats.SendMessage(text, None, 1)
		self.PrivateChatEntry.set_text("")
		
	def OnGetAUsersInfo(self, widget, prefix = ""):
		# popup
		user = input_box(self, title='Nicotine+: Get User Info',
		message='Enter the User whose User Info you wish to recieve:',
		default_text='')
		if user is None:
			pass
		else:
			self.LocalUserInfoRequest(user)
			
	def OnGetAUsersIP(self, widget, prefix = ""):
		user = input_box(self, title="Nicotine+: Get A User's IP",
		message='Enter the User whose IP Address you wish to recieve:',
		default_text='')
		if user is None:
			pass
		else:
			self.np.queue.put(slskmessages.GetPeerAddress(user))
# 			self.np.ProcessRequestToPeer(user, slskmessages.UserInfoRequest(None), self.userinfo)
			
	def OnGetAUsersShares(self, widget, prefix = ""):
		user = input_box(self, title="Nicotine+: Get A User's Shares List",
		message='Enter the User whose Shares List you wish to recieve:',
		default_text='')
		if user is None:
			pass
		else:
			self.BrowseUser(user)
			
	def traymenu(self):
		try:
			file_menu = gtk.Menu()
			connect_menu = gtk.Menu()
			
			quit_item = gtk.MenuItem("Quit")
			quit_item.connect_object("activate", self.OnExit, "file.quit")
			quit_item.show()

			ip_item = gtk.MenuItem("Lookup A User's IP")
			ip_item.connect_object("activate", self.OnGetAUsersIP, "file.ip")
			ip_item.show()
			
			userinfo_item = gtk.MenuItem("Lookup A User's Info")
			userinfo_item.connect_object("activate", self.OnGetAUsersInfo, "file.userinfo")
			userinfo_item.show()
			
			shares_item = gtk.MenuItem("Lookup A User's Shares")
			shares_item.connect_object("activate", self.OnGetAUsersShares, "file.usershares")
			shares_item.show()
			
			hide_item = gtk.MenuItem("Hide / Unhide Nicotine")
			hide_item.connect_object("activate", self.HideUnhideWindow, "file.hide")
			hide_item.show()
			
			away_item = gtk.MenuItem("Toggle Away")
			away_item.connect_object("activate", self.OnAway, "file.away")
			away_item.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("A"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)
			away_item.show()
			
			settings_item = gtk.MenuItem("Settings")
			settings_item.connect_object("activate", self.OnSettings, "settings")
			settings_item.show()
			
			connect_item = gtk.MenuItem("Connect")
			connect_item.connect_object("activate", self.OnConnect, None)
			connect_item.show()
			
			disconnect_item = gtk.MenuItem("Disconnect")
			disconnect_item.connect_object("activate", self.OnDisconnect, "disconnect")
			disconnect_item.show()
			
			connect_menu.append(connect_item)
			connect_menu.append(disconnect_item)
					
			server_menu = gtk.MenuItem("Server")
			server_menu.show()
			server_menu.set_submenu(connect_menu)
			file_menu.append(hide_item)
			file_menu.append(server_menu)
			file_menu.append(settings_item)
			file_menu.append(ip_item)
			file_menu.append(userinfo_item)
			file_menu.append(shares_item)
			file_menu.append(away_item)
			file_menu.append(quit_item)
			self.tray_menu = file_menu
			
		except Exception,e:
			print "ERROR: tray menu", e
			
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
			self.MainWindow.grab_focus()
			self.is_mapped = 1
			
	def OnTrayiconClicked(self, obj, event):
		(w, h) = self.trayicon.get_size()
		if event.x < 0 or event.y < 0 or event.x >= w or event.y >= h:
			return
# 		print event.button
		if event.button == 1:
			self.HideUnhideWindow(None)
		else:
			if event.type == gtk.gdk.BUTTON_PRESS:
				self.tray_menu.popup(None, None, None, event.button, event.time)
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

	def UpdateColours(self):
		colour = self.np.config.sections["ui"]["chatremote"]
		d = colour and {"foreground": colour} or {}
		self.tag_log = self.LogWindow.get_buffer().create_tag(**d)
		
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
	
	def OnDestroy(self, widget):
		if self.np.servertimer is not None:
		    self.np.servertimer.cancel()
		self.np.StopTimers()
		if self.np.transfers is not None:
	            self.np.transfers.AbortTransfers()
		self.np.config.writeConfig()
		self.np.protothread.abort()
		gtk.main_quit()
		
	def OnConnect(self, widget):
		self.connect1.set_sensitive(0)
		self.disconnect1.set_sensitive(1)
		if self.np.serverconn is not None:
			return
		if widget != -1:
			while not self.np.queue.empty():
				self.np.queue.get(0)
		self.SetUserStatus("...")
		server = self.np.config.sections["server"]["server"]
		self.SetStatusText("Connecting to %s:%s" %(server[0],server[1]))
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
		self.load_image(None, "disconnect")
		self.searches.interval = 0
		self.chatrooms.ConnClose()
		self.searches.ConnClose()
		self.uploads.ConnClose()
		self.downloads.ConnClose()
		self.userlist.ConnClose()
	
	def ConnectError(self, conn):
		self.connect1.set_sensitive(1)
		self.disconnect1.set_sensitive(0)
		
		self.SetUserStatus(_("Offline"))
		self.load_image(None, "disconnect")
		
	def SetUserStatus(self, status):
		self.UserStatus.pop(self.user_context_id)
		self.UserStatus.push(self.user_context_id, status)
		
	def InitInterface(self, msg):
		if self.away == 0:
			self.SetUserStatus(_("Online"))
			self.load_image(None, "connect")
			autoaway = self.np.config.sections["server"]["autoaway"]
			if autoaway > 0:
				self.awaytimer = gobject.timeout_add(1000*60*autoaway, self.OnAutoAway)
			else:
				self.awaytimer = None
		else:
			self.SetUserStatus(_("Away"))
			self.load_image(None, "away2")
		
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
			self.load_image(None, "connect")
		else:
			self.SetUserStatus(_("Away"))
			self.load_image(None, "away2")
		self.np.queue.put(slskmessages.SetStatus(self.away and 1 or 2))
		if HAVE_TRAYICON:
			pass
			
		
	def OnExit(self, widget):
		self.MainWindow.destroy()
	
	def OnSearch(self, widget):
		self.searches.OnSearch()

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
		self.DownStatus.push(self.down_context_id, _("Down: %i users, %.1f KB/s") % (usersdown,down))
		self.UpStatus.push(self.up_context_id, _("Up: %i users, %.1f KB/s") % (usersup,up))
	
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
		msg = slskmessages.RescanShares(shared, lambda: None)
		thread.start_new_thread(self.np.RescanShares, (msg,))
		
		
	def OnBuddyRescan(self, widget = None):
		if self.brescanning:
			return
		self.brescanning = 1
		
		self.rescan2.set_sensitive(False)
		self.logMessage(_("Rescanning Buddy Shares started"))
		
		shared = self.np.config.sections["transfers"]["buddyshared"][:]
		if self.np.config.sections["transfers"]["sharedownloaddir"]:
			shared.append(self.np.config.sections["transfers"]["downloaddir"])
		msg = slskmessages.RescanBuddyShares(shared, lambda: None)
		thread.start_new_thread(self.np.RescanBuddyShares, (msg,))
		
	def _BuddyRescanFinished(self, data):
		self.np.config.setBuddyShares(*data)
		self.np.config.writeShares()
		
		self.rescan2.set_sensitive(True)
		if self.np.transfers is not None:
			self.np.sendNumSharedFoldersFiles()
		self.brescanning = 0
		self.logMessage(_("Rescanning Buddy Shares finished"))
		
	def _RescanFinished(self, data):
		self.np.config.setShares(*data)
		self.np.config.writeShares()
		
		self.rescan1.set_sensitive(True)
		if self.np.transfers is not None:
			self.np.sendNumSharedFoldersFiles()
		self.rescanning = 0
		self.logMessage(_("Rescanning finished"))
		
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
		
		needrescan, config = self.settingswindow.GetSettings()
		for (key, data) in config.items():
			self.np.config.sections[key].update(data)
		
		utils.DECIMALSEP = self.np.config.sections["ui"]["decimalsep"]
		utils.CATCH_URLS = self.np.config.sections["urls"]["urlcatching"]
		utils.HUMANIZE_URLS = self.np.config.sections["urls"]["humanizeurls"]
		utils.PROTOCOL_HANDLERS = self.np.config.sections["urls"]["protocols"].copy()
		utils.PROTOCOL_HANDLERS["slsk"] = self.OnSoulSeek
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

		self.np.config.writeConfig()

		self.chatrooms.roomsctrl.UpdateColours()
		self.privatechats.UpdateColours()
		self.UpdateColours()
		self.UpdateTransferButtons()
		if needrescan:
			self.needrescan = 1
		
		if msg == "ok" and self.needrescan:
			self.needrescan = 0
			self.BothRescan()


		if self.np.config.needConfig():
			self.connect1.set_sensitive(0)
			self.logMessage(_("You need to finish configuring your settings (Server, Username, Password, Download Directory) before connecting..."))
		else:
			if self.np.transfers is None:
				self.connect1.set_sensitive(1)
				
	def UpdateTransferButtons(self):
		if self.np.config.sections["transfers"]["enabletransferbuttons"]:
			self.DownloadButtons.show()
			self.UploadButtons.show()
		else:
			self.UploadButtons.hide()
			self.DownloadButtons.hide()
			
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
					if os.path.exists(self.np.config.sections["userinfo"]["pic"]):
						has_pic = True
						f=open(self.np.config.sections["userinfo"]["pic"],'r')
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

				self.userinfo.ShowLocalInfo(user, descr, has_pic, pic, totalupl, queuesize, slotsavail)
			
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
		items[5].set_active(user in [i[0] for i in self.np.config.sections["server"]["userlist"]])
		items[6].set_active(user in self.np.config.sections["server"]["banlist"])
		items[7].set_active(user in self.np.config.sections["server"]["ignorelist"])
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
	def __init__(self, config):
		self.frame = testwin(config)
	
	def MainLoop(self):
		signal.signal(signal.SIGINT, signal.SIG_IGN)
		self.frame.MainWindow.show()
		gtk.gdk.threads_init()
		gtk.gdk.threads_enter()
		gtk.main()
		gtk.gdk.threads_leave()
