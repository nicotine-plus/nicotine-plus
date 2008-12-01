import gtk, gobject
from pynicotine.utils import _

class MainWindow:
	def __init__(self, create = True, accel_group = None, tooltips = None):
		if accel_group is None:
			self.accel_group = gtk.AccelGroup()
		else:
			self.accel_group = accel_group
		if tooltips is None:
			self.tooltips = gtk.Tooltips()
		else:
			self.tooltips = tooltips
		self.tooltips.enable()
		if create:
			self.MainWindow = gtk.Window()
			self.MainWindow.set_title(_("Nicotine"))
			self.MainWindow.set_position(gtk.WIN_POS_CENTER)
			self.MainWindow.add_accel_group(self.accel_group)
			self.MainWindow.connect("selection_get", self.OnSelectionGet)
			self.MainWindow.connect("focus_in_event", self.OnFocusIn)
			self.MainWindow.connect("focus_out_event", self.OnFocusOut)

		self.vbox1 = gtk.VBox(False, 0)
		self.vbox1.show()

		self.menubar1 = gtk.MenuBar()
		self.menubar1.show()

		self.file1 = gtk.MenuItem(_("_File"))
		self.file1.show()

		self.file1_menu = gtk.Menu()

		self.connect1 = gtk.ImageMenuItem(_("_Connect"))
		self.connect1.show()
		self.connect1.connect("activate", self.OnConnect)
		self.connect1.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("C"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

		img = gtk.image_new_from_stock(gtk.STOCK_CONNECT, gtk.ICON_SIZE_MENU)
		self.connect1.set_image(img)
		self.file1_menu.append(self.connect1)

		self.disconnect1 = gtk.ImageMenuItem(_("_Disconnect"))
		self.disconnect1.show()
		self.disconnect1.connect("activate", self.OnDisconnect)
		self.disconnect1.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("D"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

		img = gtk.image_new_from_stock(gtk.STOCK_DISCONNECT, gtk.ICON_SIZE_MENU)
		self.disconnect1.set_image(img)
		self.file1_menu.append(self.disconnect1)

		self.sep1 = gtk.MenuItem()
		self.sep1.show()

		self.file1_menu.append(self.sep1)

		self.awayreturn1 = gtk.ImageMenuItem(_("_Away/Return"))
		self.awayreturn1.show()
		self.awayreturn1.connect("activate", self.OnAway)
		self.awayreturn1.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("A"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

		img = gtk.image_new_from_stock(gtk.STOCK_MISSING_IMAGE, gtk.ICON_SIZE_MENU)
		self.awayreturn1.set_image(img)
		self.file1_menu.append(self.awayreturn1)

		self.check_privileges1 = gtk.ImageMenuItem(_("Check _privileges"))
		self.check_privileges1.show()
		self.check_privileges1.connect("activate", self.OnCheckPrivileges)

		img = gtk.image_new_from_stock(gtk.STOCK_JUMP_TO, gtk.ICON_SIZE_MENU)
		self.check_privileges1.set_image(img)
		self.file1_menu.append(self.check_privileges1)

		self.scheidingslijn1 = gtk.MenuItem()
		self.scheidingslijn1.show()

		self.file1_menu.append(self.scheidingslijn1)

		self.exit1 = gtk.ImageMenuItem(_("E_xit"))
		self.exit1.show()
		self.exit1.connect("activate", self.OnExit)
		self.exit1.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("Q"), gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)

		img = gtk.image_new_from_stock(gtk.STOCK_QUIT, gtk.ICON_SIZE_MENU)
		self.exit1.set_image(img)
		self.file1_menu.append(self.exit1)

		self.file1.set_submenu(self.file1_menu)

		self.menubar1.append(self.file1)

		self.edit1 = gtk.MenuItem(_("_Edit"))
		self.edit1.show()

		self.edit_menu = gtk.Menu()

		self.settings1 = gtk.ImageMenuItem(_("_Settings"))
		self.settings1.show()
		self.settings1.connect("activate", self.OnSettings)
		self.settings1.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("S"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

		img = gtk.image_new_from_stock(gtk.STOCK_PREFERENCES, gtk.ICON_SIZE_MENU)
		self.settings1.set_image(img)
		self.edit_menu.append(self.settings1)

		self.now_playing1 = gtk.ImageMenuItem(_("Configure _Now Playing"))
		self.now_playing1.show()
		self.now_playing1.connect("activate", self.OnNowPlayingConfigure)

		img = gtk.image_new_from_stock(gtk.STOCK_PREFERENCES, gtk.ICON_SIZE_MENU)
		self.now_playing1.set_image(img)
		self.edit_menu.append(self.now_playing1)

		self.scheidingslijn13 = gtk.MenuItem()
		self.scheidingslijn13.show()

		self.edit_menu.append(self.scheidingslijn13)

		self.BackupConfig = gtk.ImageMenuItem(_("Backup Config"))
		self.BackupConfig.show()
		self.BackupConfig.connect("activate", self.OnBackupConfig)

		img = gtk.image_new_from_stock(gtk.STOCK_SAVE, gtk.ICON_SIZE_MENU)
		self.BackupConfig.set_image(img)
		self.edit_menu.append(self.BackupConfig)

		self.edit1.set_submenu(self.edit_menu)

		self.menubar1.append(self.edit1)

		self.View = gtk.MenuItem(_("View"))
		self.View.show()

		self.menu2 = gtk.Menu()
		self.menu2.show()

		self.hide_log_window1 = gtk.CheckMenuItem(_("_Hide log window"))
		self.hide_log_window1.show()
		self.hide_log_window1.connect("activate", self.OnHideLog)
		self.hide_log_window1.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("H"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

		self.menu2.append(self.hide_log_window1)

		self.show_debug_info1 = gtk.CheckMenuItem(_("Show _debug info"))
		self.show_debug_info1.show()
		self.show_debug_info1.connect("activate", self.OnShowDebug)

		self.menu2.append(self.show_debug_info1)

		self.scheidingslijn6 = gtk.MenuItem()
		self.scheidingslijn6.show()

		self.menu2.append(self.scheidingslijn6)

		self.hide_room_list1 = gtk.CheckMenuItem(_("Hide room _list"))
		self.hide_room_list1.show()
		self.hide_room_list1.connect("activate", self.OnHideRoomList)
		self.hide_room_list1.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("R"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

		self.menu2.append(self.hide_room_list1)

		self.hide_tickers1 = gtk.CheckMenuItem(_("Hide _tickers"))
		self.hide_tickers1.show()
		self.hide_tickers1.connect("activate", self.OnHideTickers)
		self.hide_tickers1.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("T"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

		self.menu2.append(self.hide_tickers1)

		self.HideChatButtons = gtk.CheckMenuItem(_("Hide chat room log and list toggles"))
		self.HideChatButtons.show()
		self.HideChatButtons.connect("toggled", self.OnHideChatButtons)
		self.HideChatButtons.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("B"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

		self.menu2.append(self.HideChatButtons)

		self.HideFlags = gtk.CheckMenuItem(_("Hide flag columns in user lists"))
		self.HideFlags.show()
		self.HideFlags.connect("toggled", self.OnHideFlags)
		self.HideFlags.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("g"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

		self.menu2.append(self.HideFlags)

		self.sep3 = gtk.MenuItem()
		self.sep3.show()

		self.menu2.append(self.sep3)

		self.buddylist_in_tab = gtk.RadioMenuItem(None, _("Buddylist in separate tab"))
		self.buddylist_in_tab.show()
		self.buddylist_in_tab.connect("toggled", self.OnToggleBuddyList)

		self.menu2.append(self.buddylist_in_tab)

		self.buddylist_in_chatrooms1 = gtk.RadioMenuItem(self.buddylist_in_tab, _("Buddylist in Chatrooms"))
		self.buddylist_in_chatrooms1.show()
		self.buddylist_in_chatrooms1.connect("toggled", self.OnToggleBuddyList)
		self.buddylist_in_chatrooms1.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("U"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

		self.menu2.append(self.buddylist_in_chatrooms1)

		self.buddylist_always_visible = gtk.RadioMenuItem(self.buddylist_in_tab, _("Buddylist always visible"))
		self.buddylist_always_visible.show()
		self.buddylist_always_visible.connect("toggled", self.OnToggleBuddyList)

		self.menu2.append(self.buddylist_always_visible)

		self.View.set_submenu(self.menu2)

		self.menubar1.append(self.View)

		self.Shares = gtk.MenuItem(_("Shares"))
		self.Shares.show()

		self.menu1 = gtk.Menu()
		self.menu1.show()

		self.ConfigureShares = gtk.ImageMenuItem(_("Configure Shares"))
		self.ConfigureShares.show()
		self.ConfigureShares.connect("activate", self.OnSettingsShares)

		img = gtk.image_new_from_stock(gtk.STOCK_PREFERENCES, gtk.ICON_SIZE_MENU)
		self.ConfigureShares.set_image(img)
		self.menu1.append(self.ConfigureShares)

		self.separatormenuitem1 = gtk.MenuItem()
		self.separatormenuitem1.show()

		self.menu1.append(self.separatormenuitem1)

		self.rescan1 = gtk.ImageMenuItem(_("_Rescan shares"))
		self.rescan1.show()
		self.rescan1.connect("activate", self.OnRescan)

		img = gtk.image_new_from_stock(gtk.STOCK_REFRESH, gtk.ICON_SIZE_MENU)
		self.rescan1.set_image(img)
		self.menu1.append(self.rescan1)

		self.rescan_buddy = gtk.ImageMenuItem(_("_Rescan Buddy shares"))
		self.rescan_buddy.show()
		self.rescan_buddy.connect("activate", self.OnBuddyRescan)

		img = gtk.image_new_from_stock(gtk.STOCK_REFRESH, gtk.ICON_SIZE_MENU)
		self.rescan_buddy.set_image(img)
		self.menu1.append(self.rescan_buddy)

		self.scheidingslijn5 = gtk.MenuItem()
		self.scheidingslijn5.show()

		self.menu1.append(self.scheidingslijn5)

		self.rebuild1 = gtk.ImageMenuItem(_("Rebuild shares"))
		self.rebuild1.show()
		self.rebuild1.connect("activate", self.OnRebuild)

		img = gtk.image_new_from_stock(gtk.STOCK_REFRESH, gtk.ICON_SIZE_MENU)
		self.rebuild1.set_image(img)
		self.menu1.append(self.rebuild1)

		self.rebuild_buddy = gtk.ImageMenuItem(_("Rebuild Buddy shares"))
		self.rebuild_buddy.show()
		self.rebuild_buddy.connect("activate", self.OnBuddyRebuild)

		img = gtk.image_new_from_stock(gtk.STOCK_REFRESH, gtk.ICON_SIZE_MENU)
		self.rebuild_buddy.set_image(img)
		self.menu1.append(self.rebuild_buddy)

		self.scheidingslijn11 = gtk.MenuItem()
		self.scheidingslijn11.show()

		self.menu1.append(self.scheidingslijn11)

		self.browse_my_shares1 = gtk.ImageMenuItem(_("_Browse my shares"))
		self.browse_my_shares1.show()
		self.browse_my_shares1.connect("activate", self.OnBrowseMyShares)

		img = gtk.image_new_from_stock(gtk.STOCK_HARDDISK, gtk.ICON_SIZE_MENU)
		self.browse_my_shares1.set_image(img)
		self.menu1.append(self.browse_my_shares1)

		self.Shares.set_submenu(self.menu1)

		self.menubar1.append(self.Shares)

		self.modes1 = gtk.MenuItem(_("_Modes"))
		self.modes1.show()

		self.modes1_menu = gtk.Menu()

		self.chat_rooms1 = gtk.ImageMenuItem(_("_Chat Rooms"))
		self.chat_rooms1.show()
		self.chat_rooms1.connect("activate", self.OnChatRooms)

		img = gtk.image_new_from_stock(gtk.STOCK_JUMP_TO, gtk.ICON_SIZE_MENU)
		self.chat_rooms1.set_image(img)
		self.modes1_menu.append(self.chat_rooms1)

		self.private_chat1 = gtk.ImageMenuItem(_("_Private Chat"))
		self.private_chat1.show()
		self.private_chat1.connect("activate", self.OnPrivateChat)

		img = gtk.image_new_from_stock(gtk.STOCK_JUMP_TO, gtk.ICON_SIZE_MENU)
		self.private_chat1.set_image(img)
		self.modes1_menu.append(self.private_chat1)

		self.downloads1 = gtk.ImageMenuItem(_("_Downloads"))
		self.downloads1.show()
		self.downloads1.connect("activate", self.OnDownloads)

		img = gtk.image_new_from_stock(gtk.STOCK_GO_DOWN, gtk.ICON_SIZE_MENU)
		self.downloads1.set_image(img)
		self.modes1_menu.append(self.downloads1)

		self.uploads1 = gtk.ImageMenuItem(_("_Uploads"))
		self.uploads1.show()
		self.uploads1.connect("activate", self.OnUploads)

		img = gtk.image_new_from_stock(gtk.STOCK_GO_UP, gtk.ICON_SIZE_MENU)
		self.uploads1.set_image(img)
		self.modes1_menu.append(self.uploads1)

		self.search_files1 = gtk.ImageMenuItem(_("_Search Files"))
		self.search_files1.show()
		self.search_files1.connect("activate", self.OnSearchFiles)

		img = gtk.image_new_from_stock(gtk.STOCK_FIND, gtk.ICON_SIZE_MENU)
		self.search_files1.set_image(img)
		self.modes1_menu.append(self.search_files1)

		self.user_info1 = gtk.ImageMenuItem(_("User I_nfo"))
		self.user_info1.show()
		self.user_info1.connect("activate", self.OnUserInfo)

		img = gtk.image_new_from_stock(gtk.STOCK_DIALOG_INFO, gtk.ICON_SIZE_MENU)
		self.user_info1.set_image(img)
		self.modes1_menu.append(self.user_info1)

		self.user_browse1 = gtk.ImageMenuItem(_("User _Browse"))
		self.user_browse1.show()
		self.user_browse1.connect("activate", self.OnUserBrowse)

		img = gtk.image_new_from_stock(gtk.STOCK_HARDDISK, gtk.ICON_SIZE_MENU)
		self.user_browse1.set_image(img)
		self.modes1_menu.append(self.user_browse1)

		self.interests1 = gtk.ImageMenuItem(_("_Interests"))
		self.interests1.show()
		self.interests1.connect("activate", self.OnInterests)

		img = gtk.image_new_from_stock(gtk.STOCK_JUMP_TO, gtk.ICON_SIZE_MENU)
		self.interests1.set_image(img)
		self.modes1_menu.append(self.interests1)

		self.user_list1 = gtk.ImageMenuItem(_("Buddy _List"))
		self.user_list1.show()
		self.user_list1.connect("activate", self.OnUserList)

		img = gtk.image_new_from_stock(gtk.STOCK_INDEX, gtk.ICON_SIZE_MENU)
		self.user_list1.set_image(img)
		self.modes1_menu.append(self.user_list1)

		self.modes1.set_submenu(self.modes1_menu)

		self.menubar1.append(self.modes1)

		self.help1 = gtk.MenuItem(_("Hel_p"))
		self.help1.show()

		self.help1_menu = gtk.Menu()

		self.nicotine_guide1 = gtk.ImageMenuItem(_("Offline Nicotine Plus Guide"))
		self.nicotine_guide1.show()
		self.nicotine_guide1.connect("activate", self.OnNicotineGuide)
		self.nicotine_guide1.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("F1"), 0, gtk.ACCEL_VISIBLE)

		img = gtk.image_new_from_stock(gtk.STOCK_HELP, gtk.ICON_SIZE_MENU)
		self.nicotine_guide1.set_image(img)
		self.help1_menu.append(self.nicotine_guide1)

		self.nicotine_guide3 = gtk.ImageMenuItem(_("Online Nicotine Plus Guide"))
		self.nicotine_guide3.show()
		self.nicotine_guide3.connect("activate", self.OnOnlineNicotineGuide)

		img = gtk.image_new_from_stock(gtk.STOCK_HELP, gtk.ICON_SIZE_MENU)
		self.nicotine_guide3.set_image(img)
		self.help1_menu.append(self.nicotine_guide3)

		self.SourceForgeProject = gtk.ImageMenuItem(_("Sourceforge Project Website"))
		self.SourceForgeProject.show()
		self.SourceForgeProject.connect("activate", self.OnSourceForgeProject)

		img = gtk.image_new_from_stock(gtk.STOCK_HOME, gtk.ICON_SIZE_MENU)
		self.SourceForgeProject.set_image(img)
		self.help1_menu.append(self.SourceForgeProject)

		self.Trac = gtk.ImageMenuItem(_("Nicotine-Plus Trac Website"))
		self.Trac.show()
		self.Trac.connect("activate", self.OnTrac)

		img = gtk.image_new_from_stock(gtk.STOCK_DIALOG_QUESTION, gtk.ICON_SIZE_MENU)
		self.Trac.set_image(img)
		self.help1_menu.append(self.Trac)

		self.separator1 = gtk.MenuItem()
		self.separator1.show()

		self.help1_menu.append(self.separator1)

		self.about_chatroom_commands1 = gtk.ImageMenuItem(_("About _chat room commands"))
		self.about_chatroom_commands1.show()
		self.about_chatroom_commands1.connect("activate", self.OnAboutChatroomCommands)

		img = gtk.image_new_from_stock(gtk.STOCK_HELP, gtk.ICON_SIZE_MENU)
		self.about_chatroom_commands1.set_image(img)
		self.help1_menu.append(self.about_chatroom_commands1)

		self.about_private_chat_command1 = gtk.ImageMenuItem(_("About _private chat commands"))
		self.about_private_chat_command1.show()
		self.about_private_chat_command1.connect("activate", self.OnAboutPrivateChatCommands)

		img = gtk.image_new_from_stock(gtk.STOCK_HELP, gtk.ICON_SIZE_MENU)
		self.about_private_chat_command1.set_image(img)
		self.help1_menu.append(self.about_private_chat_command1)

		self.about_dependencies = gtk.ImageMenuItem(_("About _optional dependencies"))
		self.about_dependencies.show()
		self.about_dependencies.connect("activate", self.OnAboutDependencies)

		img = gtk.image_new_from_stock(gtk.STOCK_HELP, gtk.ICON_SIZE_MENU)
		self.about_dependencies.set_image(img)
		self.help1_menu.append(self.about_dependencies)

		self.scheidingslijn4 = gtk.MenuItem()
		self.scheidingslijn4.show()

		self.help1_menu.append(self.scheidingslijn4)

		self.about_search_filters1 = gtk.ImageMenuItem(_("About _search filters"))
		self.about_search_filters1.show()
		self.about_search_filters1.connect("activate", self.OnAboutFilters)

		img = gtk.image_new_from_stock(gtk.STOCK_HELP, gtk.ICON_SIZE_MENU)
		self.about_search_filters1.set_image(img)
		self.help1_menu.append(self.about_search_filters1)

		self.scheidingslijn3 = gtk.MenuItem()
		self.scheidingslijn3.show()

		self.help1_menu.append(self.scheidingslijn3)

		self.check_latest1 = gtk.ImageMenuItem(_("Check _latest"))
		self.check_latest1.show()
		self.check_latest1.connect("activate", self.OnCheckLatest)

		img = gtk.image_new_from_stock(gtk.STOCK_CONNECT, gtk.ICON_SIZE_MENU)
		self.check_latest1.set_image(img)
		self.help1_menu.append(self.check_latest1)

		self.scheidingslijn7 = gtk.MenuItem()
		self.scheidingslijn7.show()

		self.help1_menu.append(self.scheidingslijn7)

		self.about_nicotine1 = gtk.ImageMenuItem(_("About _Nicotine"))
		self.about_nicotine1.show()
		self.about_nicotine1.connect("activate", self.OnAbout)

		img = gtk.image_new_from_stock(gtk.STOCK_ABOUT, gtk.ICON_SIZE_MENU)
		self.about_nicotine1.set_image(img)
		self.help1_menu.append(self.about_nicotine1)

		self.help1.set_submenu(self.help1_menu)

		self.menubar1.append(self.help1)

		self.vbox1.pack_start(self.menubar1, False, False, 0)

		self.vpaned1 = gtk.VPaned()
		self.vpaned1.show()

		self.hpanedm = gtk.HPaned()
		self.hpanedm.show()

		self.MainNotebook = gtk.Notebook()
		self.MainNotebook.set_scrollable(True)
		self.MainNotebook.show()
		self.MainNotebook.connect("switch_page", self.OnSwitchPage)

		self.hpaned1 = gtk.HPaned()
		self.hpaned1.show()
		self.hpaned1.set_border_width(3)

		self.ChatNotebook = self.get_custom_widget("ChatNotebook", "", "", 0, 0)
		self.ChatNotebook.show()
		self.hpaned1.pack1(self.ChatNotebook, True, True)

		self.vpaned3 = gtk.VPaned()
		self.vpaned3.show()

		self.hpaned1.pack2(self.vpaned3, False, True)

		self.ChatTabLabel = self.get_custom_widget("ChatTabLabel", "hpaned1", _("Chat rooms"), 0, 0)
		self.ChatTabLabel.show()
		self.privatevbox = gtk.VBox(False, 0)
		self.privatevbox.show()
		self.privatevbox.set_spacing(5)
		self.privatevbox.set_border_width(5)

		self.hbox20 = gtk.HBox(False, 0)
		self.hbox20.show()
		self.hbox20.set_spacing(5)

		self.UserPrivateCombo = self.get_custom_widget("UserPrivateCombo", "", "", 0, 0)
		self.UserPrivateCombo.show()
		self.hbox20.pack_start(self.UserPrivateCombo, False, True, 0)

		self.sPrivateChatButton = gtk.Button()
		self.sPrivateChatButton.show()

		self.alignment10 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment10.show()

		self.hbox30 = gtk.HBox(False, 0)
		self.hbox30.show()
		self.hbox30.set_spacing(2)

		self.image10 = gtk.Image()
		self.image10.set_from_stock(gtk.STOCK_JUMP_TO, 4)
		self.image10.show()
		self.hbox30.pack_start(self.image10, False, False, 0)

		self.label39 = gtk.Label(_("Start Message"))
		self.label39.show()
		self.hbox30.pack_end(self.label39, False, False, 0)

		self.alignment10.add(self.hbox30)

		self.sPrivateChatButton.add(self.alignment10)

		self.hbox20.pack_start(self.sPrivateChatButton, False, False, 0)

		self.configureLog = gtk.Button()
		self.configureLog.show()
		self.configureLog.connect("clicked", self.OnSettingsLogging)

		self.alignment38 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment38.show()

		self.hbox27 = gtk.HBox(False, 0)
		self.hbox27.show()
		self.hbox27.set_spacing(2)

		self.image28 = gtk.Image()
		self.image28.set_from_stock(gtk.STOCK_PREFERENCES, 4)
		self.image28.show()
		self.hbox27.pack_start(self.image28, False, False, 0)

		self.alignment38.add(self.hbox27)

		self.configureLog.add(self.alignment38)

		self.hbox20.pack_end(self.configureLog, False, False, 0)

		self.privatevbox.pack_start(self.hbox20, False, True, 0)

		self.PrivatechatNotebook = self.get_custom_widget("PrivatechatNotebook", "", "", 0, 0)
		self.PrivatechatNotebook.show()
		self.privatevbox.pack_start(self.PrivatechatNotebook)

		self.PrivateChatTabLabel = self.get_custom_widget("PrivateChatTabLabel", "privatevbox", _("Private chat"), 0, 0)
		self.PrivateChatTabLabel.show()
		self.vboxdownloads = gtk.VBox(False, 0)
		self.vboxdownloads.show()

		self.hbox3 = gtk.HBox(False, 0)
		self.hbox3.show()
		self.hbox3.set_spacing(5)

		self.DownloadUsers = gtk.Label(_("Users: 0"))
		self.DownloadUsers.set_alignment(0, 0.50)
		self.DownloadUsers.set_padding(5, 0)
		self.DownloadUsers.show()
		self.DownloadUsers.set_width_chars(10)
		self.hbox3.pack_start(self.DownloadUsers, False, True, 0)

		self.DownloadFiles = gtk.Label(_("Files: 0"))
		self.DownloadFiles.show()
		self.DownloadFiles.set_width_chars(15)
		self.hbox3.pack_start(self.DownloadFiles, False, True, 0)

		self.Spacer5 = gtk.Label()
		self.Spacer5.show()
		self.hbox3.pack_start(self.Spacer5)

		self.ExpandDownloads = gtk.ToggleButton()
		self.tooltips.set_tip(self.ExpandDownloads, _("Expand / Collapse all"))
		self.ExpandDownloads.show()

		self.ExpandDownloadsImage = gtk.Image()
		self.ExpandDownloadsImage.set_from_stock(gtk.STOCK_REMOVE, 4)
		self.ExpandDownloadsImage.show()
		self.ExpandDownloads.add(self.ExpandDownloadsImage)

		self.hbox3.pack_start(self.ExpandDownloads, False, True, 0)

		self.ToggleTreeDownloads = gtk.CheckButton()
		self.ToggleTreeDownloads.set_label(_("Group by Users"))
		self.ToggleTreeDownloads.show()

		self.hbox3.pack_start(self.ToggleTreeDownloads, False, False, 0)

		self.ToggleAutoRetry = gtk.CheckButton()
		self.tooltips.set_tip(self.ToggleAutoRetry, _("Every 3 minutes"))
		self.ToggleAutoRetry.set_label(_("Auto-retry failed"))
		self.ToggleAutoRetry.show()

		self.hbox3.pack_start(self.ToggleAutoRetry, False, False, 0)

		self.configureTransfers1 = gtk.Button()
		self.configureTransfers1.show()
		self.configureTransfers1.connect("clicked", self.OnSettingsTransfers)

		self.alignment46 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment46.show()

		self.hbox59 = gtk.HBox(False, 0)
		self.hbox59.show()
		self.hbox59.set_spacing(2)

		self.image41 = gtk.Image()
		self.image41.set_from_stock(gtk.STOCK_PREFERENCES, 4)
		self.image41.show()
		self.hbox59.pack_start(self.image41, False, False, 0)

		self.alignment46.add(self.hbox59)

		self.configureTransfers1.add(self.alignment46)

		self.hbox3.pack_end(self.configureTransfers1, False, False, 0)

		self.vboxdownloads.pack_start(self.hbox3, False, False, 2)

		self.scrolledwindow29 = gtk.ScrolledWindow()
		self.scrolledwindow29.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.scrolledwindow29.show()

		self.DownloadList = gtk.TreeView()
		self.DownloadList.show()
		self.scrolledwindow29.add(self.DownloadList)

		self.vboxdownloads.pack_start(self.scrolledwindow29)

		self.DownloadButtons = gtk.HBox(False, 0)
		self.DownloadButtons.show()
		self.DownloadButtons.set_spacing(5)

		self.clearFinishedAbortedButton = gtk.Button()
		self.clearFinishedAbortedButton.show()

		self.alignment21 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment21.show()

		self.hbox41 = gtk.HBox(False, 0)
		self.hbox41.show()
		self.hbox41.set_spacing(2)

		self.image21 = gtk.Image()
		self.image21.set_from_stock(gtk.STOCK_CLEAR, 4)
		self.image21.show()
		self.hbox41.pack_start(self.image21, False, False, 0)

		self.label50 = gtk.Label(_("Clear Finished / Aborted"))
		self.label50.show()
		self.hbox41.pack_start(self.label50, False, False, 0)

		self.alignment21.add(self.hbox41)

		self.clearFinishedAbortedButton.add(self.alignment21)

		self.DownloadButtons.pack_start(self.clearFinishedAbortedButton, False, False, 0)

		self.clearQueuedButton = gtk.Button()
		self.clearQueuedButton.show()

		self.alignment22 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment22.show()

		self.hbox42 = gtk.HBox(False, 0)
		self.hbox42.show()
		self.hbox42.set_spacing(2)

		self.image22 = gtk.Image()
		self.image22.set_from_stock(gtk.STOCK_CLEAR, 4)
		self.image22.show()
		self.hbox42.pack_start(self.image22, False, False, 0)

		self.label51 = gtk.Label(_("Clear Queued"))
		self.label51.show()
		self.hbox42.pack_start(self.label51, False, False, 0)

		self.alignment22.add(self.hbox42)

		self.clearQueuedButton.add(self.alignment22)

		self.DownloadButtons.pack_start(self.clearQueuedButton, False, False, 0)

		self.retryTransferButton = gtk.Button()
		self.retryTransferButton.show()

		self.alignment15 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment15.show()

		self.hbox35 = gtk.HBox(False, 0)
		self.hbox35.show()
		self.hbox35.set_spacing(2)

		self.image15 = gtk.Image()
		self.image15.set_from_stock(gtk.STOCK_REDO, 4)
		self.image15.show()
		self.hbox35.pack_start(self.image15, False, False, 0)

		self.label44 = gtk.Label(_("Retry"))
		self.label44.show()
		self.hbox35.pack_start(self.label44, False, False, 0)

		self.alignment15.add(self.hbox35)

		self.retryTransferButton.add(self.alignment15)

		self.DownloadButtons.pack_start(self.retryTransferButton, False, False, 1)

		self.abortTransferButton = gtk.Button()
		self.abortTransferButton.show()

		self.alignment16 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment16.show()

		self.hbox36 = gtk.HBox(False, 0)
		self.hbox36.show()
		self.hbox36.set_spacing(2)

		self.image16 = gtk.Image()
		self.image16.set_from_stock(gtk.STOCK_CANCEL, 4)
		self.image16.show()
		self.hbox36.pack_start(self.image16, False, False, 0)

		self.label45 = gtk.Label(_("Abort"))
		self.label45.show()
		self.hbox36.pack_start(self.label45, False, False, 0)

		self.alignment16.add(self.hbox36)

		self.abortTransferButton.add(self.alignment16)

		self.DownloadButtons.pack_start(self.abortTransferButton, False, False, 0)

		self.deleteTransferButton = gtk.Button()
		self.deleteTransferButton.show()

		self.alignment9 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment9.show()

		self.hbox29 = gtk.HBox(False, 0)
		self.hbox29.show()
		self.hbox29.set_spacing(2)

		self.image9 = gtk.Image()
		self.image9.set_from_stock(gtk.STOCK_DELETE, 4)
		self.image9.show()
		self.hbox29.pack_start(self.image9, False, False, 0)

		self.label38 = gtk.Label(_("Abort & Delete"))
		self.label38.show()
		self.hbox29.pack_start(self.label38, False, False, 0)

		self.alignment9.add(self.hbox29)

		self.deleteTransferButton.add(self.alignment9)

		self.DownloadButtons.pack_start(self.deleteTransferButton, False, False, 0)

		self.banDownloadButton = gtk.Button()
		self.banDownloadButton.show()

		self.alignment13 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment13.show()

		self.hbox33 = gtk.HBox(False, 0)
		self.hbox33.show()
		self.hbox33.set_spacing(2)

		self.image13 = gtk.Image()
		self.image13.set_from_stock(gtk.STOCK_STOP, 4)
		self.image13.show()
		self.hbox33.pack_start(self.image13, False, False, 0)

		self.label42 = gtk.Label(_("Ban User(s)"))
		self.label42.show()
		self.hbox33.pack_start(self.label42, False, False, 0)

		self.alignment13.add(self.hbox33)

		self.banDownloadButton.add(self.alignment13)

		self.DownloadButtons.pack_end(self.banDownloadButton, False, False, 0)

		self.vboxdownloads.pack_start(self.DownloadButtons, False, True, 3)

		self.DownloadsTabLabel = self.get_custom_widget("DownloadsTabLabel", "vboxdownloads", _("Downloads"), 0, 0)
		self.DownloadsTabLabel.show()
		self.vboxuploads = gtk.VBox(False, 0)
		self.vboxuploads.show()

		self.hbox13 = gtk.HBox(False, 0)
		self.hbox13.show()
		self.hbox13.set_spacing(5)

		self.UploadUsers = gtk.Label(_("Users: 0"))
		self.UploadUsers.set_alignment(0, 0.50)
		self.UploadUsers.set_padding(5, 0)
		self.UploadUsers.show()
		self.UploadUsers.set_width_chars(10)
		self.hbox13.pack_start(self.UploadUsers, False, True, 0)

		self.UploadFiles = gtk.Label(_("Files: 0"))
		self.UploadFiles.show()
		self.UploadFiles.set_width_chars(15)
		self.hbox13.pack_start(self.UploadFiles, False, True, 0)

		self.Spacer1 = gtk.Label()
		self.Spacer1.show()
		self.hbox13.pack_start(self.Spacer1)

		self.ExpandUploads = gtk.ToggleButton()
		self.tooltips.set_tip(self.ExpandUploads, _("Expand / Collapse all"))
		self.ExpandUploads.set_active(True)
		self.ExpandUploads.show()

		self.ExpandUploadsImage = gtk.Image()
		self.ExpandUploadsImage.set_from_stock(gtk.STOCK_REMOVE, 4)
		self.ExpandUploadsImage.show()
		self.ExpandUploads.add(self.ExpandUploadsImage)

		self.hbox13.pack_start(self.ExpandUploads, False, True, 0)

		self.ToggleTreeUploads = gtk.CheckButton()
		self.ToggleTreeUploads.set_label(_("Group by Users"))
		self.ToggleTreeUploads.show()

		self.hbox13.pack_start(self.ToggleTreeUploads, False, False, 0)

		self.ToggleAutoclear = gtk.CheckButton()
		self.ToggleAutoclear.set_label(_("Autoclear Finished"))
		self.ToggleAutoclear.show()

		self.hbox13.pack_start(self.ToggleAutoclear, False, False, 0)

		self.configureTransfers2 = gtk.Button()
		self.configureTransfers2.show()
		self.configureTransfers2.connect("clicked", self.OnSettingsTransfers)

		self.alignment49 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment49.show()

		self.hbox69 = gtk.HBox(False, 0)
		self.hbox69.show()
		self.hbox69.set_spacing(2)

		self.image43 = gtk.Image()
		self.image43.set_from_stock(gtk.STOCK_PREFERENCES, 4)
		self.image43.show()
		self.hbox69.pack_start(self.image43, False, False, 0)

		self.alignment49.add(self.hbox69)

		self.configureTransfers2.add(self.alignment49)

		self.hbox13.pack_end(self.configureTransfers2, False, False, 0)

		self.vboxuploads.pack_start(self.hbox13, False, False, 2)

		self.scrolledwindow30 = gtk.ScrolledWindow()
		self.scrolledwindow30.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.scrolledwindow30.show()

		self.UploadList = gtk.TreeView()
		self.UploadList.show()
		self.scrolledwindow30.add(self.UploadList)

		self.vboxuploads.pack_start(self.scrolledwindow30)

		self.UploadButtons = gtk.HBox(False, 0)
		self.UploadButtons.show()
		self.UploadButtons.set_spacing(5)

		self.clearUploadFinishedAbortedButton = gtk.Button()
		self.clearUploadFinishedAbortedButton.show()

		self.alignment20 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment20.show()

		self.hbox40 = gtk.HBox(False, 0)
		self.hbox40.show()
		self.hbox40.set_spacing(2)

		self.image20 = gtk.Image()
		self.image20.set_from_stock(gtk.STOCK_CLEAR, 4)
		self.image20.show()
		self.hbox40.pack_start(self.image20, False, False, 0)

		self.label49 = gtk.Label(_("Clear Finished / Aborted"))
		self.label49.show()
		self.hbox40.pack_start(self.label49, False, False, 0)

		self.alignment20.add(self.hbox40)

		self.clearUploadFinishedAbortedButton.add(self.alignment20)

		self.UploadButtons.pack_start(self.clearUploadFinishedAbortedButton, False, False, 0)

		self.clearUploadQueueButton = gtk.Button()
		self.clearUploadQueueButton.show()

		self.alignment19 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment19.show()

		self.hbox39 = gtk.HBox(False, 0)
		self.hbox39.show()
		self.hbox39.set_spacing(2)

		self.image19 = gtk.Image()
		self.image19.set_from_stock(gtk.STOCK_CLEAR, 4)
		self.image19.show()
		self.hbox39.pack_start(self.image19, False, False, 0)

		self.label48 = gtk.Label(_("Clear Queued"))
		self.label48.show()
		self.hbox39.pack_start(self.label48, False, False, 0)

		self.alignment19.add(self.hbox39)

		self.clearUploadQueueButton.add(self.alignment19)

		self.UploadButtons.pack_start(self.clearUploadQueueButton, False, False, 0)

		self.abortUploadButton = gtk.Button()
		self.abortUploadButton.show()

		self.alignment17 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment17.show()

		self.hbox37 = gtk.HBox(False, 0)
		self.hbox37.show()
		self.hbox37.set_spacing(2)

		self.image17 = gtk.Image()
		self.image17.set_from_stock(gtk.STOCK_CANCEL, 4)
		self.image17.show()
		self.hbox37.pack_start(self.image17, False, False, 0)

		self.label46 = gtk.Label(_("Abort"))
		self.label46.show()
		self.hbox37.pack_start(self.label46, False, False, 0)

		self.alignment17.add(self.hbox37)

		self.abortUploadButton.add(self.alignment17)

		self.UploadButtons.pack_start(self.abortUploadButton, False, False, 0)

		self.abortUserUploadButton = gtk.Button()
		self.abortUserUploadButton.show()

		self.alignment18 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment18.show()

		self.hbox38 = gtk.HBox(False, 0)
		self.hbox38.show()
		self.hbox38.set_spacing(2)

		self.image18 = gtk.Image()
		self.image18.set_from_stock(gtk.STOCK_CANCEL, 4)
		self.image18.show()
		self.hbox38.pack_start(self.image18, False, False, 0)

		self.label47 = gtk.Label(_("Abort User's Upload(s)"))
		self.label47.show()
		self.hbox38.pack_start(self.label47, False, False, 0)

		self.alignment18.add(self.hbox38)

		self.abortUserUploadButton.add(self.alignment18)

		self.UploadButtons.pack_start(self.abortUserUploadButton, False, False, 0)

		self.banUploadButton = gtk.Button()
		self.banUploadButton.show()

		self.alignment14 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment14.show()

		self.hbox34 = gtk.HBox(False, 0)
		self.hbox34.show()
		self.hbox34.set_spacing(2)

		self.image14 = gtk.Image()
		self.image14.set_from_stock(gtk.STOCK_STOP, 4)
		self.image14.show()
		self.hbox34.pack_start(self.image14, False, False, 0)

		self.label43 = gtk.Label(_("Ban User(s)"))
		self.label43.show()
		self.hbox34.pack_start(self.label43, False, False, 0)

		self.alignment14.add(self.hbox34)

		self.banUploadButton.add(self.alignment14)

		self.UploadButtons.pack_end(self.banUploadButton, False, False, 0)

		self.vboxuploads.pack_start(self.UploadButtons, False, True, 3)

		self.UploadsTabLabel = self.get_custom_widget("UploadsTabLabel", "vboxuploads", _("Uploads"), 0, 0)
		self.UploadsTabLabel.show()
		self.searchvbox = gtk.VBox(False, 0)
		self.searchvbox.show()
		self.searchvbox.set_spacing(5)
		self.searchvbox.set_border_width(5)

		self.hbox2 = gtk.HBox(False, 0)
		self.hbox2.show()
		self.hbox2.set_spacing(5)

		self.WishList = gtk.Button()
		self.WishList.show()

		self.alignment8 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment8.show()

		self.hbox18 = gtk.HBox(False, 0)
		self.hbox18.show()
		self.hbox18.set_spacing(2)

		self.image8 = gtk.Image()
		self.image8.set_from_stock(gtk.STOCK_EDIT, 4)
		self.image8.show()
		self.hbox18.pack_start(self.image8, False, False, 0)

		self.label2 = gtk.Label(_("WishList"))
		self.label2.show()
		self.hbox18.pack_start(self.label2, False, False, 0)

		self.alignment8.add(self.hbox18)

		self.WishList.add(self.alignment8)

		self.hbox2.pack_start(self.WishList, False, False, 0)

		self.SearchEntryCombo_List = gtk.ListStore(gobject.TYPE_STRING)
		self.SearchEntryCombo = gtk.ComboBoxEntry()
		self.SearchEntryCombo.show()

		self.SearchEntry = self.SearchEntryCombo.child
		self.tooltips.set_tip(self.SearchEntry, _("Search patterns: with a word = term, without a word = -term"))
		self.SearchEntry.connect("activate", self.OnSearch)

		self.SearchEntryCombo.set_model(self.SearchEntryCombo_List)
		self.SearchEntryCombo.set_text_column(0)
		self.hbox2.pack_start(self.SearchEntryCombo)

		self.ClearSearchHistory = gtk.Button()
		self.tooltips.set_tip(self.ClearSearchHistory, _("Clear all searches attempts"))
		self.ClearSearchHistory.show()
		self.ClearSearchHistory.connect("clicked", self.OnClearSearchHistory)

		self.image38 = gtk.Image()
		self.image38.set_from_stock(gtk.STOCK_CLEAR, 4)
		self.image38.show()
		self.ClearSearchHistory.add(self.image38)

		self.hbox2.pack_start(self.ClearSearchHistory, False, False, 0)

		self.SearchButton = gtk.Button()
		self.SearchButton.show()
		self.SearchButton.connect("clicked", self.OnSearch)

		self.alignment3 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment3.show()

		self.hbox23 = gtk.HBox(False, 0)
		self.hbox23.show()
		self.hbox23.set_spacing(2)

		self.image3 = gtk.Image()
		self.image3.set_from_stock(gtk.STOCK_FIND, 4)
		self.image3.show()
		self.hbox23.pack_start(self.image3, False, False, 0)

		self.label32 = gtk.Label(_("Search"))
		self.label32.show()
		self.hbox23.pack_start(self.label32, False, False, 0)

		self.alignment3.add(self.hbox23)

		self.SearchButton.add(self.alignment3)

		self.hbox2.pack_start(self.SearchButton, False, False, 0)

		self.UserSearchCombo = self.get_custom_widget("UserSearchCombo", "", "", 0, 0)
		self.UserSearchCombo.show()
		self.hbox2.pack_start(self.UserSearchCombo, False, False, 0)

		self.RoomSearchCombo_List = gtk.ListStore(gobject.TYPE_STRING)
		self.RoomSearchCombo = gtk.ComboBoxEntry()
		self.RoomSearchCombo.show()
		self.RoomSearchCombo.set_sensitive(False)

		self.RoomSearchEntry = self.RoomSearchCombo.child

		self.RoomSearchCombo.set_model(self.RoomSearchCombo_List)
		self.RoomSearchCombo.set_text_column(0)
		self.hbox2.pack_start(self.RoomSearchCombo, False, False, 0)

		self.SearchMethod_List = gtk.ListStore(gobject.TYPE_STRING)
		self.SearchMethod = gtk.ComboBox()
		self.SearchMethod.show()
		for i in [_("")]:
			self.SearchMethod_List.append([i])

		self.SearchMethod.set_model(self.SearchMethod_List)
		cell = gtk.CellRendererText()
		self.SearchMethod.pack_start(cell, True)
		self.SearchMethod.add_attribute(cell, 'text', 0)
		self.hbox2.pack_start(self.SearchMethod, False, False, 0)

		self.configureSearches = gtk.Button()
		self.configureSearches.show()
		self.configureSearches.connect("clicked", self.OnSettingsSearches)

		self.alignment50 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment50.show()

		self.hbox71 = gtk.HBox(False, 0)
		self.hbox71.show()
		self.hbox71.set_spacing(2)

		self.image44 = gtk.Image()
		self.image44.set_from_stock(gtk.STOCK_PREFERENCES, 4)
		self.image44.show()
		self.hbox71.pack_start(self.image44, False, False, 0)

		self.alignment50.add(self.hbox71)

		self.configureSearches.add(self.alignment50)

		self.hbox2.pack_end(self.configureSearches, False, False, 0)

		self.searchvbox.pack_start(self.hbox2, False, True, 0)

		self.SearchNotebook = self.get_custom_widget("SearchNotebook", "", "", 0, 0)
		self.SearchNotebook.show()
		self.searchvbox.pack_start(self.SearchNotebook)

		self.SearchTabLabel = self.get_custom_widget("SearchTabLabel", "searchvbox", _("Search files"), 0, 0)
		self.SearchTabLabel.show()
		self.userinfovbox = gtk.VBox(False, 0)
		self.userinfovbox.show()
		self.userinfovbox.set_spacing(5)
		self.userinfovbox.set_border_width(5)

		self.hbox21 = gtk.HBox(False, 0)
		self.hbox21.show()
		self.hbox21.set_spacing(5)

		self.UserInfoCombo = self.get_custom_widget("UserInfoCombo", "", "", 0, 0)
		self.UserInfoCombo.show()
		self.hbox21.pack_start(self.UserInfoCombo, False, True, 0)

		self.sUserinfoButton = gtk.Button()
		self.sUserinfoButton.show()

		self.alignment12 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment12.show()

		self.hbox32 = gtk.HBox(False, 0)
		self.hbox32.show()
		self.hbox32.set_spacing(2)

		self.image12 = gtk.Image()
		self.image12.set_from_stock(gtk.STOCK_JUMP_TO, 4)
		self.image12.show()
		self.hbox32.pack_start(self.image12, False, False, 0)

		self.label41 = gtk.Label(_("Get Userinfo"))
		self.label41.show()
		self.hbox32.pack_start(self.label41, False, False, 0)

		self.alignment12.add(self.hbox32)

		self.sUserinfoButton.add(self.alignment12)

		self.hbox21.pack_start(self.sUserinfoButton, False, False, 0)

		self.configureUserinfo = gtk.Button()
		self.configureUserinfo.show()
		self.configureUserinfo.connect("clicked", self.OnSettingsUserinfo)

		self.alignment51 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment51.show()

		self.hbox72 = gtk.HBox(False, 0)
		self.hbox72.show()
		self.hbox72.set_spacing(2)

		self.image45 = gtk.Image()
		self.image45.set_from_stock(gtk.STOCK_PREFERENCES, 4)
		self.image45.show()
		self.hbox72.pack_start(self.image45, False, False, 0)

		self.alignment51.add(self.hbox72)

		self.configureUserinfo.add(self.alignment51)

		self.hbox21.pack_end(self.configureUserinfo, False, False, 0)

		self.userinfovbox.pack_start(self.hbox21, False, True, 0)

		self.UserInfoNotebook = self.get_custom_widget("UserInfoNotebook", "", "", 0, 0)
		self.UserInfoNotebook.show()
		self.userinfovbox.pack_start(self.UserInfoNotebook)

		self.UserInfoTabLabel = self.get_custom_widget("UserInfoTabLabel", "userinfovbox", _("User info"), 0, 0)
		self.UserInfoTabLabel.show()
		self.userbrowsevbox = gtk.VBox(False, 0)
		self.userbrowsevbox.show()
		self.userbrowsevbox.set_spacing(5)
		self.userbrowsevbox.set_border_width(5)

		self.hbox22 = gtk.HBox(False, 0)
		self.hbox22.show()
		self.hbox22.set_spacing(5)

		self.UserBrowseCombo = self.get_custom_widget("UserBrowseCombo", "", "", 0, 0)
		self.UserBrowseCombo.show()
		self.hbox22.pack_start(self.UserBrowseCombo, False, True, 0)

		self.sSharesButton = gtk.Button()
		self.sSharesButton.show()

		self.alignment11 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment11.show()

		self.hbox31 = gtk.HBox(False, 0)
		self.hbox31.show()
		self.hbox31.set_spacing(2)

		self.image11 = gtk.Image()
		self.image11.set_from_stock(gtk.STOCK_JUMP_TO, 4)
		self.image11.show()
		self.hbox31.pack_start(self.image11, False, False, 0)

		self.label40 = gtk.Label(_("Browse Shares"))
		self.label40.show()
		self.hbox31.pack_start(self.label40, False, False, 0)

		self.alignment11.add(self.hbox31)

		self.sSharesButton.add(self.alignment11)

		self.hbox22.pack_start(self.sSharesButton, False, False, 0)

		self.LoadFromDisk = gtk.Button()
		self.LoadFromDisk.show()
		self.LoadFromDisk.connect("clicked", self.OnLoadFromDisk)

		self.alignment39 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment39.show()

		self.hbox60 = gtk.HBox(False, 0)
		self.hbox60.show()
		self.hbox60.set_spacing(2)

		self.image310 = gtk.Image()
		self.image310.set_from_stock(gtk.STOCK_OPEN, 4)
		self.image310.show()
		self.hbox60.pack_start(self.image310, False, False, 0)

		self.label68 = gtk.Label(_("Load From Disk"))
		self.label68.show()
		self.hbox60.pack_start(self.label68, False, False, 0)

		self.alignment39.add(self.hbox60)

		self.LoadFromDisk.add(self.alignment39)

		self.hbox22.pack_start(self.LoadFromDisk, False, False, 0)

		self.configureShares = gtk.Button()
		self.configureShares.show()
		self.configureShares.connect("clicked", self.OnSettingsShares)

		self.alignment52 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment52.show()

		self.hbox73 = gtk.HBox(False, 0)
		self.hbox73.show()
		self.hbox73.set_spacing(2)

		self.image46 = gtk.Image()
		self.image46.set_from_stock(gtk.STOCK_PREFERENCES, 4)
		self.image46.show()
		self.hbox73.pack_start(self.image46, False, False, 0)

		self.alignment52.add(self.hbox73)

		self.configureShares.add(self.alignment52)

		self.hbox22.pack_end(self.configureShares, False, False, 0)

		self.userbrowsevbox.pack_start(self.hbox22, False, True, 0)

		self.UserBrowseNotebook = self.get_custom_widget("UserBrowseNotebook", "", "", 0, 0)
		self.UserBrowseNotebook.show()
		self.userbrowsevbox.pack_start(self.UserBrowseNotebook)

		self.UserBrowseTabLabel = self.get_custom_widget("UserBrowseTabLabel", "userbrowsevbox", _("User browse"), 0, 0)
		self.UserBrowseTabLabel.show()
		self.interests = gtk.VBox(False, 0)
		self.interests.show()
		self.interests.set_spacing(10)
		self.interests.set_border_width(10)

		self.hbox12 = gtk.HBox(False, 0)
		self.hbox12.show()
		self.hbox12.set_spacing(5)

		self.SimilarUsersButton = gtk.Button()
		self.SimilarUsersButton.show()
		self.SimilarUsersButton.connect("clicked", self.OnSimilarUsersClicked)

		self.alignment6 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment6.show()

		self.hbox26 = gtk.HBox(False, 0)
		self.hbox26.show()
		self.hbox26.set_spacing(2)

		self.image6 = gtk.Image()
		self.image6.set_from_stock(gtk.STOCK_REFRESH, 4)
		self.image6.show()
		self.hbox26.pack_start(self.image6, False, False, 0)

		self.label35 = gtk.Label(_("Similar users"))
		self.label35.show()
		self.hbox26.pack_start(self.label35, False, False, 0)

		self.alignment6.add(self.hbox26)

		self.SimilarUsersButton.add(self.alignment6)

		self.hbox12.pack_end(self.SimilarUsersButton, False, False, 0)

		self.GlobalRecommendationsButton = gtk.Button()
		self.GlobalRecommendationsButton.show()
		self.GlobalRecommendationsButton.connect("clicked", self.OnGlobalRecommendationsClicked)

		self.alignment4 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment4.show()

		self.hbox24 = gtk.HBox(False, 0)
		self.hbox24.show()
		self.hbox24.set_spacing(2)

		self.image4 = gtk.Image()
		self.image4.set_from_stock(gtk.STOCK_REFRESH, 4)
		self.image4.show()
		self.hbox24.pack_start(self.image4, False, False, 0)

		self.label33 = gtk.Label(_("Global recommendations"))
		self.label33.show()
		self.hbox24.pack_start(self.label33, False, False, 0)

		self.alignment4.add(self.hbox24)

		self.GlobalRecommendationsButton.add(self.alignment4)

		self.hbox12.pack_end(self.GlobalRecommendationsButton, False, False, 0)

		self.RecommendationsButton = gtk.Button()
		self.RecommendationsButton.show()
		self.RecommendationsButton.connect("clicked", self.OnRecommendationsClicked)

		self.alignment5 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment5.show()

		self.hbox25 = gtk.HBox(False, 0)
		self.hbox25.show()
		self.hbox25.set_spacing(2)

		self.image5 = gtk.Image()
		self.image5.set_from_stock(gtk.STOCK_REFRESH, 4)
		self.image5.show()
		self.hbox25.pack_start(self.image5, False, False, 0)

		self.label34 = gtk.Label(_("Recommendations"))
		self.label34.show()
		self.hbox25.pack_start(self.label34, False, False, 0)

		self.alignment5.add(self.hbox25)

		self.RecommendationsButton.add(self.alignment5)

		self.hbox12.pack_end(self.RecommendationsButton, False, False, 0)

		self.interests.pack_start(self.hbox12, False, True, 0)

		self.hbox11 = gtk.HBox(False, 0)
		self.hbox11.show()
		self.hbox11.set_spacing(5)

		self.hpaned3 = gtk.HPaned()
		self.hpaned3.show()

		self.vbox13 = gtk.VBox(True, 0)
		self.vbox13.set_size_request(200, -1)
		self.vbox13.show()
		self.vbox13.set_spacing(10)

		self.vbox14 = gtk.VBox(False, 0)
		self.vbox14.show()
		self.vbox14.set_spacing(5)

		self.scrolledwindow23 = gtk.ScrolledWindow()
		self.scrolledwindow23.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.scrolledwindow23.show()
		self.scrolledwindow23.set_shadow_type(gtk.SHADOW_IN)

		self.LikesList = gtk.TreeView()
		self.LikesList.show()
		self.scrolledwindow23.add(self.LikesList)

		self.vbox14.pack_start(self.scrolledwindow23)

		self.button15 = gtk.Button()
		self.button15.show()
		self.button15.connect("clicked", self.OnAddThingILike)

		self.alignment2 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment2.show()

		self.hbox15 = gtk.HBox(False, 0)
		self.hbox15.show()
		self.hbox15.set_spacing(2)

		self.image2 = gtk.Image()
		self.image2.set_from_stock(gtk.STOCK_ADD, 4)
		self.image2.show()
		self.hbox15.pack_start(self.image2, False, False, 0)

		self.label22 = gtk.Label(_("Add"))
		self.label22.show()
		self.hbox15.pack_start(self.label22, False, False, 0)

		self.alignment2.add(self.hbox15)

		self.button15.add(self.alignment2)

		self.vbox14.pack_start(self.button15, False, False, 0)

		self.vbox13.pack_start(self.vbox14)

		self.vbox15 = gtk.VBox(False, 0)
		self.vbox15.show()
		self.vbox15.set_spacing(5)

		self.scrolledwindow24 = gtk.ScrolledWindow()
		self.scrolledwindow24.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.scrolledwindow24.show()
		self.scrolledwindow24.set_shadow_type(gtk.SHADOW_IN)

		self.DislikesList = gtk.TreeView()
		self.DislikesList.show()
		self.scrolledwindow24.add(self.DislikesList)

		self.vbox15.pack_start(self.scrolledwindow24)

		self.button16 = gtk.Button()
		self.button16.show()
		self.button16.connect("clicked", self.OnAddThingIDislike)

		self.alignment1 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment1.show()

		self.hbox14 = gtk.HBox(False, 0)
		self.hbox14.show()
		self.hbox14.set_spacing(2)

		self.image1 = gtk.Image()
		self.image1.set_from_stock(gtk.STOCK_ADD, 4)
		self.image1.show()
		self.hbox14.pack_start(self.image1, False, False, 0)

		self.label21 = gtk.Label(_("Add"))
		self.label21.show()
		self.hbox14.pack_start(self.label21, False, False, 0)

		self.alignment1.add(self.hbox14)

		self.button16.add(self.alignment1)

		self.vbox15.pack_start(self.button16, False, False, 0)

		self.vbox13.pack_start(self.vbox15)

		self.hpaned3.pack1(self.vbox13, False, True)

		self.hpaned4 = gtk.HPaned()
		self.hpaned4.show()

		self.RecommendationsVbox = gtk.VBox(False, 0)
		self.RecommendationsVbox.show()

		self.RecommendationsExpander = gtk.Expander()
		self.RecommendationsExpander.set_expanded(True)
		self.RecommendationsExpander.show()

		self.vbox8 = gtk.VBox(False, 0)
		self.vbox8.show()

		self.RecScrolledWindow = gtk.ScrolledWindow()
		self.RecScrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.RecScrolledWindow.show()
		self.RecScrolledWindow.set_shadow_type(gtk.SHADOW_IN)

		self.RecommendationsList = gtk.TreeView()
		self.RecommendationsList.show()
		self.RecScrolledWindow.add(self.RecommendationsList)

		self.vbox8.pack_start(self.RecScrolledWindow)

		self.RecommendationsExpander.add(self.vbox8)

		self.RecommendationsLabel = gtk.Label(_("Recommendations"))
		self.RecommendationsLabel.show()
		self.RecommendationsExpander.set_label_widget(self.RecommendationsLabel)

		self.RecommendationsVbox.pack_start(self.RecommendationsExpander)

		self.UnrecommendationsExpander = gtk.Expander()
		self.UnrecommendationsExpander.show()

		self.UnRecScrolledWindow = gtk.ScrolledWindow()
		self.UnRecScrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.UnRecScrolledWindow.show()
		self.UnRecScrolledWindow.set_shadow_type(gtk.SHADOW_IN)

		self.UnrecommendationsList = gtk.TreeView()
		self.UnrecommendationsList.show()
		self.UnRecScrolledWindow.add(self.UnrecommendationsList)

		self.UnrecommendationsExpander.add(self.UnRecScrolledWindow)

		self.UnrecommendationsLabel = gtk.Label(_("Unrecommendations"))
		self.UnrecommendationsLabel.show()
		self.UnrecommendationsExpander.set_label_widget(self.UnrecommendationsLabel)

		self.RecommendationsVbox.pack_start(self.UnrecommendationsExpander, False, True, 0)

		self.hpaned4.pack1(self.RecommendationsVbox, True, True)

		self.scrolledwindow27 = gtk.ScrolledWindow()
		self.scrolledwindow27.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.scrolledwindow27.show()
		self.scrolledwindow27.set_shadow_type(gtk.SHADOW_IN)

		self.RecommendationUsersList = gtk.TreeView()
		self.RecommendationUsersList.show()
		self.scrolledwindow27.add(self.RecommendationUsersList)

		self.hpaned4.pack2(self.scrolledwindow27, True, True)

		self.hpaned3.pack2(self.hpaned4, True, True)

		self.hbox11.pack_start(self.hpaned3)

		self.interests.pack_start(self.hbox11)

		self.InterestsTabLabel = self.get_custom_widget("InterestsTabLabel", "interests", _("Interests"), 0, 0)
		self.InterestsTabLabel.show()
		self.MainNotebook.append_page(self.hpaned1, self.ChatTabLabel)

		self.MainNotebook.append_page(self.privatevbox, self.PrivateChatTabLabel)

		self.MainNotebook.append_page(self.vboxdownloads, self.DownloadsTabLabel)

		self.MainNotebook.append_page(self.vboxuploads, self.UploadsTabLabel)

		self.MainNotebook.append_page(self.searchvbox, self.SearchTabLabel)

		self.MainNotebook.append_page(self.userinfovbox, self.UserInfoTabLabel)

		self.MainNotebook.append_page(self.userbrowsevbox, self.UserBrowseTabLabel)

		self.MainNotebook.append_page(self.interests, self.InterestsTabLabel)

		self.hpanedm.pack1(self.MainNotebook, True, True)

		self.vpanedm = gtk.VPaned()
		self.vpanedm.show()

		self.hpanedm.pack2(self.vpanedm, True, True)

		self.vpaned1.pack1(self.hpanedm, True, False)

		self.vbox1.pack_start(self.vpaned1)

		self.hbox10 = gtk.HBox(False, 0)
		self.hbox10.show()
		self.hbox10.set_border_width(2)

		self.Statusbar = gtk.Statusbar()
		self.Statusbar.set_has_resize_grip(False)
		self.Statusbar.show()
		self.Statusbar.set_border_width(1)
		self.hbox10.pack_start(self.Statusbar)

		self.SharesProgress = gtk.ProgressBar()
		self.SharesProgress.set_text(_("Scanning Shares"))
		self.hbox10.pack_start(self.SharesProgress, False, False, 0)

		self.BuddySharesProgress = gtk.ProgressBar()
		self.BuddySharesProgress.set_text(_("Scanning Buddy Shares"))
		self.hbox10.pack_start(self.BuddySharesProgress, False, False, 0)

		self.UserStatus = gtk.Statusbar()
		self.UserStatus.set_size_request(80, -1)
		self.UserStatus.set_has_resize_grip(False)
		self.UserStatus.show()
		self.UserStatus.set_border_width(1)
		self.hbox10.pack_start(self.UserStatus, False, True, 0)

		self.SocketStatus = gtk.Statusbar()
		self.SocketStatus.set_size_request(130, -1)
		self.SocketStatus.set_has_resize_grip(False)
		self.SocketStatus.show()
		self.SocketStatus.set_border_width(1)
		self.hbox10.pack_start(self.SocketStatus, False, True, 0)

		self.DownStatus = gtk.Statusbar()
		self.DownStatus.set_size_request(190, -1)
		self.DownStatus.set_has_resize_grip(False)
		self.DownStatus.show()
		self.DownStatus.set_border_width(1)
		self.hbox10.pack_start(self.DownStatus, False, True, 0)

		self.UpStatus = gtk.Statusbar()
		self.UpStatus.set_size_request(180, -1)
		self.UpStatus.set_has_resize_grip(False)
		self.UpStatus.show()
		self.UpStatus.set_border_width(1)
		self.hbox10.pack_start(self.UpStatus, False, True, 0)

		self.vbox1.pack_start(self.hbox10, False, False, 0)


		if create:
			self.MainWindow.add(self.vbox1)

	def OnSelectionGet(self, widget):
		pass

	def OnFocusIn(self, widget):
		pass

	def OnFocusOut(self, widget):
		pass

	def OnConnect(self, widget):
		pass

	def OnDisconnect(self, widget):
		pass

	def OnAway(self, widget):
		pass

	def OnCheckPrivileges(self, widget):
		pass

	def OnExit(self, widget):
		pass

	def OnSettings(self, widget):
		pass

	def OnNowPlayingConfigure(self, widget):
		pass

	def OnBackupConfig(self, widget):
		pass

	def OnHideLog(self, widget):
		pass

	def OnShowDebug(self, widget):
		pass

	def OnHideRoomList(self, widget):
		pass

	def OnHideTickers(self, widget):
		pass

	def OnHideChatButtons(self, widget):
		pass

	def OnHideFlags(self, widget):
		pass

	def OnToggleBuddyList(self, widget):
		pass

	def OnSettingsShares(self, widget):
		pass

	def OnRescan(self, widget):
		pass

	def OnBuddyRescan(self, widget):
		pass

	def OnRebuild(self, widget):
		pass

	def OnBuddyRebuild(self, widget):
		pass

	def OnBrowseMyShares(self, widget):
		pass

	def OnChatRooms(self, widget):
		pass

	def OnPrivateChat(self, widget):
		pass

	def OnDownloads(self, widget):
		pass

	def OnUploads(self, widget):
		pass

	def OnSearchFiles(self, widget):
		pass

	def OnUserInfo(self, widget):
		pass

	def OnUserBrowse(self, widget):
		pass

	def OnInterests(self, widget):
		pass

	def OnUserList(self, widget):
		pass

	def OnNicotineGuide(self, widget):
		pass

	def OnOnlineNicotineGuide(self, widget):
		pass

	def OnSourceForgeProject(self, widget):
		pass

	def OnTrac(self, widget):
		pass

	def OnAboutChatroomCommands(self, widget):
		pass

	def OnAboutPrivateChatCommands(self, widget):
		pass

	def OnAboutDependencies(self, widget):
		pass

	def OnAboutFilters(self, widget):
		pass

	def OnCheckLatest(self, widget):
		pass

	def OnAbout(self, widget):
		pass

	def OnSwitchPage(self, widget):
		pass

	def OnSettingsLogging(self, widget):
		pass

	def OnSettingsTransfers(self, widget):
		pass

	def OnSearch(self, widget):
		pass

	def OnClearSearchHistory(self, widget):
		pass

	def OnSettingsSearches(self, widget):
		pass

	def OnSettingsUserinfo(self, widget):
		pass

	def OnLoadFromDisk(self, widget):
		pass

	def OnSimilarUsersClicked(self, widget):
		pass

	def OnGlobalRecommendationsClicked(self, widget):
		pass

	def OnRecommendationsClicked(self, widget):
		pass

	def OnAddThingILike(self, widget):
		pass

	def OnAddThingIDislike(self, widget):
		pass

	def get_custom_widget(self, id, string1, string2, int1, int2):
		w = gtk.Label(_("(custom widget: %s)") % id)
		return w

