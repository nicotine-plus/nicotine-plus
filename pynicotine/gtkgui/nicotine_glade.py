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

		self.scheidingslijn8 = gtk.MenuItem()
		self.scheidingslijn8.show()

		self.edit_menu.append(self.scheidingslijn8)

		self.hide_log_window1 = gtk.CheckMenuItem(_("_Hide log window"))
		self.hide_log_window1.show()
		self.hide_log_window1.connect("activate", self.OnHideLog)
		self.hide_log_window1.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("H"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

		self.edit_menu.append(self.hide_log_window1)

		self.show_debug_info1 = gtk.CheckMenuItem(_("Show _debug info"))
		self.show_debug_info1.show()
		self.show_debug_info1.connect("activate", self.OnShowDebug)

		self.edit_menu.append(self.show_debug_info1)

		self.scheidingslijn6 = gtk.MenuItem()
		self.scheidingslijn6.show()

		self.edit_menu.append(self.scheidingslijn6)

		self.hide_room_list1 = gtk.CheckMenuItem(_("Hide room _list"))
		self.hide_room_list1.show()
		self.hide_room_list1.connect("activate", self.OnHideRoomList)
		self.hide_room_list1.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("R"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

		self.edit_menu.append(self.hide_room_list1)

		self.hide_tickers1 = gtk.CheckMenuItem(_("Hide _tickers"))
		self.hide_tickers1.show()
		self.hide_tickers1.connect("activate", self.OnHideTickers)
		self.hide_tickers1.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("T"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

		self.edit_menu.append(self.hide_tickers1)

		self.HideChatButtons = gtk.CheckMenuItem(_("Hide chat room log and list toggles"))
		self.HideChatButtons.show()
		self.HideChatButtons.connect("toggled", self.OnHideChatButtons)
		self.HideChatButtons.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("T"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

		self.edit_menu.append(self.HideChatButtons)

		self.buddylist_in_chatrooms1 = gtk.CheckMenuItem(_("Buddylist in Chatrooms"))
		self.buddylist_in_chatrooms1.show()
		self.buddylist_in_chatrooms1.connect("activate", self.OnToggleBuddyList)
		self.buddylist_in_chatrooms1.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("U"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

		self.edit_menu.append(self.buddylist_in_chatrooms1)

		self.scheidingslijn5 = gtk.MenuItem()
		self.scheidingslijn5.show()

		self.edit_menu.append(self.scheidingslijn5)

		self.rescan1 = gtk.ImageMenuItem(_("_Rescan shares"))
		self.rescan1.show()
		self.rescan1.connect("activate", self.OnRescan)

		img = gtk.image_new_from_stock(gtk.STOCK_REFRESH, gtk.ICON_SIZE_MENU)
		self.rescan1.set_image(img)
		self.edit_menu.append(self.rescan1)

		self.rescan2 = gtk.ImageMenuItem(_("_Rescan Buddy shares"))
		self.rescan2.show()
		self.rescan2.connect("activate", self.OnBuddyRescan)

		img = gtk.image_new_from_stock(gtk.STOCK_REFRESH, gtk.ICON_SIZE_MENU)
		self.rescan2.set_image(img)
		self.edit_menu.append(self.rescan2)

		self.browse_my_shares1 = gtk.ImageMenuItem(_("_Browse my shares"))
		self.browse_my_shares1.show()
		self.browse_my_shares1.connect("activate", self.OnBrowseMyShares)

		img = gtk.image_new_from_stock(gtk.STOCK_HARDDISK, gtk.ICON_SIZE_MENU)
		self.browse_my_shares1.set_image(img)
		self.edit_menu.append(self.browse_my_shares1)

		self.edit1.set_submenu(self.edit_menu)

		self.menubar1.append(self.edit1)

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

		self.abour_search_filters1 = gtk.ImageMenuItem(_("About _search filters"))
		self.abour_search_filters1.show()
		self.abour_search_filters1.connect("activate", self.OnAboutFilters)

		img = gtk.image_new_from_stock(gtk.STOCK_HELP, gtk.ICON_SIZE_MENU)
		self.abour_search_filters1.set_image(img)
		self.help1_menu.append(self.abour_search_filters1)

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

		self.MainNotebook = gtk.Notebook()
		self.MainNotebook.set_size_request(0, 0)
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

		self.ChatTabLabel = self.get_custom_widget("ChatTabLabel", "ImageLabel", _("Chat rooms"), 0, 0)
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

		self.privatevbox.pack_start(self.hbox20, False, True, 0)

		self.PrivatechatNotebook = self.get_custom_widget("PrivatechatNotebook", "", "", 0, 0)
		self.PrivatechatNotebook.show()
		self.privatevbox.pack_start(self.PrivatechatNotebook)

		self.PrivateChatTabLabel = self.get_custom_widget("PrivateChatTabLabel", "ImageLabel", _("Private chat"), 0, 0)
		self.PrivateChatTabLabel.show()
		self.vboxdownloads = gtk.VBox(False, 0)
		self.vboxdownloads.show()

		self.hbox3 = gtk.HBox(False, 0)
		self.hbox3.show()
		self.hbox3.set_spacing(5)

		self.ToggleTreeDownloads = gtk.CheckButton()
		self.ToggleTreeDownloads.set_label(_("Group by Users"))
		self.ToggleTreeDownloads.show()

		self.hbox3.pack_end(self.ToggleTreeDownloads, False, False, 0)

		self.ExpandDownloads = gtk.ToggleButton()
		self.ExpandDownloads.set_label(_("Expand / Collapse all"))
		self.ExpandDownloads.show()

		self.hbox3.pack_end(self.ExpandDownloads, False, True, 0)

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

		self.DownloadsTabLabel = self.get_custom_widget("DownloadsTabLabel", "ImageLabel", _("Downloads"), 0, 0)
		self.DownloadsTabLabel.show()
		self.vboxuploads = gtk.VBox(False, 0)
		self.vboxuploads.show()

		self.hbox13 = gtk.HBox(False, 0)
		self.hbox13.show()
		self.hbox13.set_spacing(5)

		self.Spacer1 = gtk.Label()
		self.Spacer1.show()
		self.hbox13.pack_start(self.Spacer1)

		self.ExpandUploads = gtk.ToggleButton()
		self.ExpandUploads.set_label(_("Expand / Collapse all"))
		self.ExpandUploads.show()

		self.hbox13.pack_start(self.ExpandUploads, False, True, 0)

		self.ToggleTreeUploads = gtk.CheckButton()
		self.ToggleTreeUploads.set_label(_("Group by Users"))
		self.ToggleTreeUploads.show()

		self.hbox13.pack_start(self.ToggleTreeUploads, False, False, 0)

		self.ToggleAutoclear = gtk.CheckButton()
		self.ToggleAutoclear.set_label(_("Autoclear Finished"))
		self.ToggleAutoclear.show()

		self.hbox13.pack_start(self.ToggleAutoclear, False, False, 0)

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

		self.UploadsTabLabel = self.get_custom_widget("UploadsTabLabel", "ImageLabel", _("Uploads"), 0, 0)
		self.UploadsTabLabel.show()
		self.searchvbox = gtk.VBox(False, 0)
		self.searchvbox.show()
		self.searchvbox.set_spacing(5)
		self.searchvbox.set_border_width(5)

		self.hbox2 = gtk.HBox(False, 0)
		self.hbox2.show()
		self.hbox2.set_spacing(8)

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

		self.ClearSearchHistory = gtk.Button()
		self.ClearSearchHistory.show()
		self.ClearSearchHistory.connect("clicked", self.OnClearSearchHistory)

		self.alignment38 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment38.show()

		self.hbox59 = gtk.HBox(False, 0)
		self.hbox59.show()
		self.hbox59.set_spacing(2)

		self.image38 = gtk.Image()
		self.image38.set_from_stock(gtk.STOCK_CLEAR, 4)
		self.image38.show()
		self.hbox59.pack_start(self.image38, False, False, 0)

		self.label67 = gtk.Label(_("Clear"))
		self.label67.show()
		self.hbox59.pack_start(self.label67, False, False, 0)

		self.alignment38.add(self.hbox59)

		self.ClearSearchHistory.add(self.alignment38)

		self.hbox2.pack_start(self.ClearSearchHistory, False, False, 0)

		self.UserSearchCombo = self.get_custom_widget("UserSearchCombo", "", "", 0, 0)
		self.UserSearchCombo.show()
		self.hbox2.pack_start(self.UserSearchCombo, False, False, 0)

		self.RoomSearchCombo_List = gtk.ListStore(gobject.TYPE_STRING)
		self.RoomSearchCombo = gtk.ComboBoxEntry()
		self.RoomSearchCombo.show()
		self.RoomSearchCombo.set_sensitive(False)

		self.comboboxentry_entry2 = self.RoomSearchCombo.child

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

		self.searchvbox.pack_start(self.hbox2, False, True, 0)

		self.SearchNotebook = self.get_custom_widget("SearchNotebook", "", "", 0, 0)
		self.SearchNotebook.show()
		self.searchvbox.pack_start(self.SearchNotebook)

		self.SearchTabLabel = self.get_custom_widget("SearchTabLabel", "ImageLabel", _("Search files"), 0, 0)
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

		self.userinfovbox.pack_start(self.hbox21, False, True, 0)

		self.UserInfoNotebook = self.get_custom_widget("UserInfoNotebook", "", "", 0, 0)
		self.UserInfoNotebook.show()
		self.userinfovbox.pack_start(self.UserInfoNotebook)

		self.UserInfoTabLabel = self.get_custom_widget("UserInfoTabLabel", "ImageLabel", _("User info"), 0, 0)
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

		self.userbrowsevbox.pack_start(self.hbox22, False, True, 0)

		self.UserBrowseNotebook = self.get_custom_widget("UserBrowseNotebook", "", "", 0, 0)
		self.UserBrowseNotebook.show()
		self.userbrowsevbox.pack_start(self.UserBrowseNotebook)

		self.UserBrowseTabLabel = self.get_custom_widget("UserBrowseTabLabel", "ImageLabel", _("User browse"), 0, 0)
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

		self.InterestsTabLabel = self.get_custom_widget("InterestsTabLabel", "ImageLabel", _("Interests"), 0, 0)
		self.InterestsTabLabel.show()
		self.MainNotebook.append_page(self.hpaned1, self.ChatTabLabel)

		self.MainNotebook.append_page(self.privatevbox, self.PrivateChatTabLabel)

		self.MainNotebook.append_page(self.vboxdownloads, self.DownloadsTabLabel)

		self.MainNotebook.append_page(self.vboxuploads, self.UploadsTabLabel)

		self.MainNotebook.append_page(self.searchvbox, self.SearchTabLabel)

		self.MainNotebook.append_page(self.userinfovbox, self.UserInfoTabLabel)

		self.MainNotebook.append_page(self.userbrowsevbox, self.UserBrowseTabLabel)

		self.MainNotebook.append_page(self.interests, self.InterestsTabLabel)

		self.vpaned1.pack1(self.MainNotebook, True, True)

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
		self.UserStatus.set_size_request(100, -1)
		self.UserStatus.set_has_resize_grip(False)
		self.UserStatus.show()
		self.UserStatus.set_border_width(1)
		self.hbox10.pack_start(self.UserStatus, False, True, 0)

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

	def OnToggleBuddyList(self, widget):
		pass

	def OnRescan(self, widget):
		pass

	def OnBuddyRescan(self, widget):
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

	def OnSearch(self, widget):
		pass

	def OnClearSearchHistory(self, widget):
		pass

	def OnLoadFromDisk(self, widget):
		pass

	def OnSimilarUsersClicked(self, widget):
		pass

	def OnRecommendationsClicked(self, widget):
		pass

	def OnGlobalRecommendationsClicked(self, widget):
		pass

	def OnAddThingILike(self, widget):
		pass

	def OnAddThingIDislike(self, widget):
		pass

	def get_custom_widget(self, id, string1, string2, int1, int2):
		w = gtk.Label(_("(custom widget: %s)") % id)
		return w

class ChatRoomTab:
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
			self.ChatRoomTab = gtk.Window()
			self.ChatRoomTab.set_title(_("window1"))
			self.ChatRoomTab.add_accel_group(self.accel_group)
			self.ChatRoomTab.show()

		self.Main = gtk.VBox(False, 0)
		self.Main.show()

		self.hbox7 = gtk.HBox(False, 0)
		self.hbox7.show()

		self.Ticker = self.get_custom_widget("Ticker", "", "", 0, 0)
		self.Ticker.connect("button_press_event", self.OnTickerClicked)
		self.hbox7.pack_start(self.Ticker)

		self.HideUserList = gtk.ToggleButton()
		self.tooltips.set_tip(self.HideUserList, _("Hide/Show User list"))
		self.HideUserList.show()
		self.HideUserList.connect("toggled", self.OnHideUserList)

		self.alignment47 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment47.show()

		self.hbox70 = gtk.HBox(False, 0)
		self.hbox70.show()

		self.HideUserListImage = gtk.Image()
		self.HideUserListImage.set_from_stock(gtk.STOCK_GO_FORWARD, 1)
		self.HideUserListImage.show()
		self.hbox70.pack_start(self.HideUserListImage, False, False, 0)

		self.alignment47.add(self.hbox70)

		self.HideUserList.add(self.alignment47)

		self.hbox7.pack_end(self.HideUserList, False, False, 0)

		self.HideStatusLog = gtk.ToggleButton()
		self.tooltips.set_tip(self.HideStatusLog, _("Hide/Show Status log"))
		self.HideStatusLog.show()
		self.HideStatusLog.connect("toggled", self.OnHideStatusLog)

		self.alignment44 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment44.show()

		self.hbox67 = gtk.HBox(False, 0)
		self.hbox67.show()

		self.HideStatusLogImage = gtk.Image()
		self.HideStatusLogImage.set_from_stock(gtk.STOCK_GO_UP, 1)
		self.HideStatusLogImage.show()
		self.hbox67.pack_start(self.HideStatusLogImage, False, False, 0)

		self.alignment44.add(self.hbox67)

		self.HideStatusLog.add(self.alignment44)

		self.hbox7.pack_end(self.HideStatusLog, False, False, 0)

		self.ShowChatHelp = gtk.Button()
		self.tooltips.set_tip(self.ShowChatHelp, _("Chat room command help"))
		self.ShowChatHelp.show()
		self.ShowChatHelp.connect("clicked", self.OnShowChatHelp)

		self.alignment28 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment28.show()

		self.hbox47 = gtk.HBox(False, 0)
		self.hbox47.show()

		self.image39 = gtk.Image()
		self.image39.set_from_stock(gtk.STOCK_HELP, 1)
		self.image39.show()
		self.hbox47.pack_start(self.image39, False, False, 0)

		self.alignment28.add(self.hbox47)

		self.ShowChatHelp.add(self.alignment28)

		self.hbox7.pack_end(self.ShowChatHelp, False, False, 0)

		self.Main.pack_start(self.hbox7, False, True, 0)

		self.Hpaned = gtk.HPaned()
		self.Hpaned.show()

		self.Vpaned = gtk.VPaned()
		self.Vpaned.show()

		self.RoomLogWindow = gtk.ScrolledWindow()
		self.RoomLogWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.RoomLogWindow.show()
		self.RoomLogWindow.set_shadow_type(gtk.SHADOW_IN)

		self.RoomLog = gtk.TextView()
		self.RoomLog.set_cursor_visible(False)
		self.RoomLog.set_editable(False)
		self.RoomLog.show()
		self.RoomLogWindow.add(self.RoomLog)

		self.Vpaned.pack1(self.RoomLogWindow, False, True)

		self.vbox6 = gtk.VBox(False, 0)
		self.vbox6.show()

		self.ChatScrollWindow = gtk.ScrolledWindow()
		self.ChatScrollWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.ChatScrollWindow.show()
		self.ChatScrollWindow.set_shadow_type(gtk.SHADOW_IN)

		self.ChatScroll = gtk.TextView()
		self.ChatScroll.set_wrap_mode(gtk.WRAP_WORD)
		self.ChatScroll.set_cursor_visible(False)
		self.ChatScroll.set_editable(False)
		self.ChatScroll.show()
		self.ChatScrollWindow.add(self.ChatScroll)

		self.vbox6.pack_start(self.ChatScrollWindow)

		self.ChatEntry = gtk.Entry()
		self.ChatEntry.show()
		self.ChatEntry.connect("activate", self.OnEnter)
		self.ChatEntry.connect("key_press_event", self.OnKeyPress)
		self.vbox6.pack_start(self.ChatEntry, False, False, 0)

		self.Vpaned.pack2(self.vbox6, True, False)

		self.Hpaned.pack1(self.Vpaned, True, True)

		self.vbox5 = gtk.VBox(False, 0)
		self.vbox5.show()

		self.LabelPeople = gtk.Label(_("0 people in room"))
		self.LabelPeople.show()
		self.vbox5.pack_start(self.LabelPeople, False, False, 2)

		self.scrolledwindow14 = gtk.ScrolledWindow()
		self.scrolledwindow14.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.scrolledwindow14.show()
		self.scrolledwindow14.set_shadow_type(gtk.SHADOW_IN)

		self.UserList = gtk.TreeView()
		self.UserList.show()
		self.scrolledwindow14.add(self.UserList)

		self.vbox5.pack_start(self.scrolledwindow14)

		self.hbox58 = gtk.HBox(False, 0)
		self.hbox58.show()
		self.hbox58.set_spacing(5)
		self.hbox58.set_border_width(3)

		self.Log = gtk.CheckButton()
		self.Log.set_label(_("Log"))
		self.Log.show()
		self.Log.connect("toggled", self.OnLogToggled)

		self.hbox58.pack_start(self.Log, False, False, 0)

		self.Encoding_List = gtk.ListStore(gobject.TYPE_STRING)
		self.Encoding = gtk.ComboBox()
		self.Encoding.show()
		self.Encoding.connect("changed", self.OnEncodingChanged)

		self.Encoding.set_model(self.Encoding_List)
		cell = gtk.CellRendererText()
		self.Encoding.pack_start(cell, True)
		self.Encoding.add_attribute(cell, 'text', 0)
		self.hbox58.pack_start(self.Encoding)

		self.vbox5.pack_start(self.hbox58, False, False, 0)

		self.hbox4 = gtk.HBox(False, 0)
		self.hbox4.show()
		self.hbox4.set_border_width(3)

		self.AutoJoin = gtk.CheckButton()
		self.AutoJoin.set_label(_("Auto-join"))
		self.AutoJoin.show()
		self.AutoJoin.connect("toggled", self.OnAutojoin)

		self.hbox4.pack_start(self.AutoJoin, False, False, 0)

		self.Leave = gtk.Button()
		self.Leave.show()
		self.Leave.connect("clicked", self.OnLeave)

		self.alignment33 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment33.show()

		self.hbox53 = gtk.HBox(False, 0)
		self.hbox53.show()
		self.hbox53.set_spacing(2)

		self.image33 = gtk.Image()
		self.image33.set_from_stock(gtk.STOCK_CLOSE, 4)
		self.image33.show()
		self.hbox53.pack_start(self.image33, False, False, 0)

		self.label62 = gtk.Label(_("Leave"))
		self.label62.show()
		self.hbox53.pack_start(self.label62, False, False, 0)

		self.alignment33.add(self.hbox53)

		self.Leave.add(self.alignment33)

		self.hbox4.pack_end(self.Leave, False, False, 0)

		self.vbox5.pack_start(self.hbox4, False, True, 0)

		self.Hpaned.pack2(self.vbox5, False, True)

		self.Main.pack_start(self.Hpaned)


		if create:
			self.ChatRoomTab.add(self.Main)

	def OnTickerClicked(self, widget):
		pass

	def OnHideUserList(self, widget):
		pass

	def OnHideStatusLog(self, widget):
		pass

	def OnShowChatHelp(self, widget):
		pass

	def OnEnter(self, widget):
		pass

	def OnKeyPress(self, widget):
		pass

	def OnLogToggled(self, widget):
		pass

	def OnEncodingChanged(self, widget):
		pass

	def OnAutojoin(self, widget):
		pass

	def OnLeave(self, widget):
		pass

	def get_custom_widget(self, id, string1, string2, int1, int2):
		w = gtk.Label(_("(custom widget: %s)") % id)
		return w

class PrivateChatTab:
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
			self.PrivateChatTab = gtk.Window()
			self.PrivateChatTab.set_title(_("window1"))
			self.PrivateChatTab.add_accel_group(self.accel_group)
			self.PrivateChatTab.show()

		self.Main = gtk.VBox(False, 0)
		self.Main.show()

		self.scrolledwindow16 = gtk.ScrolledWindow()
		self.scrolledwindow16.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.scrolledwindow16.show()
		self.scrolledwindow16.set_shadow_type(gtk.SHADOW_IN)

		self.ChatScroll = gtk.TextView()
		self.ChatScroll.set_wrap_mode(gtk.WRAP_WORD)
		self.ChatScroll.set_cursor_visible(False)
		self.ChatScroll.set_editable(False)
		self.ChatScroll.show()
		self.scrolledwindow16.add(self.ChatScroll)

		self.Main.pack_start(self.scrolledwindow16)

		self.hbox5 = gtk.HBox(False, 0)
		self.hbox5.show()
		self.hbox5.set_spacing(5)
		self.hbox5.set_border_width(3)

		self.ChatLine = gtk.Entry()
		self.ChatLine.show()
		self.ChatLine.connect("activate", self.OnEnter)
		self.ChatLine.connect("key_press_event", self.OnKeyPress)
		self.hbox5.pack_start(self.ChatLine)

		self.Encoding_List = gtk.ListStore(gobject.TYPE_STRING)
		self.Encoding = gtk.ComboBox()
		self.Encoding.show()
		self.Encoding.connect("changed", self.OnEncodingChanged)

		self.Encoding.set_model(self.Encoding_List)
		cell = gtk.CellRendererText()
		self.Encoding.pack_start(cell, True)
		self.Encoding.add_attribute(cell, 'text', 0)
		self.hbox5.pack_start(self.Encoding, False, False, 0)

		self.PeerPrivateMessages = gtk.CheckButton()
		self.tooltips.set_tip(self.PeerPrivateMessages, _("Send the private message directly to the user (not supported on most clients)"))
		self.PeerPrivateMessages.set_label(_("Direct"))
		self.PeerPrivateMessages.show()

		self.hbox5.pack_start(self.PeerPrivateMessages, False, False, 0)

		self.Log = gtk.CheckButton()
		self.Log.set_label(_("Log"))
		self.Log.show()
		self.Log.connect("toggled", self.OnLogToggled)

		self.hbox5.pack_start(self.Log, False, False, 0)

		self.button1 = gtk.Button()
		self.button1.show()
		self.button1.connect("clicked", self.OnClose)

		self.alignment34 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment34.show()

		self.hbox54 = gtk.HBox(False, 0)
		self.hbox54.show()
		self.hbox54.set_spacing(2)

		self.image34 = gtk.Image()
		self.image34.set_from_stock(gtk.STOCK_CLOSE, 4)
		self.image34.show()
		self.hbox54.pack_start(self.image34, False, False, 0)

		self.label63 = gtk.Label(_("Close"))
		self.label63.show()
		self.hbox54.pack_start(self.label63, False, False, 0)

		self.alignment34.add(self.hbox54)

		self.button1.add(self.alignment34)

		self.hbox5.pack_start(self.button1, False, False, 0)

		self.Main.pack_start(self.hbox5, False, True, 0)


		if create:
			self.PrivateChatTab.add(self.Main)

	def OnEnter(self, widget):
		pass

	def OnKeyPress(self, widget):
		pass

	def OnEncodingChanged(self, widget):
		pass

	def OnLogToggled(self, widget):
		pass

	def OnClose(self, widget):
		pass

	def get_custom_widget(self, id, string1, string2, int1, int2):
		w = gtk.Label(_("(custom widget: %s)") % id)
		return w

class SearchTab:
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
			self.SearchTab = gtk.Window()
			self.SearchTab.set_title(_("window1"))
			self.SearchTab.add_accel_group(self.accel_group)
			self.SearchTab.show()

		self.vbox7 = gtk.VBox(False, 0)
		self.vbox7.show()
		self.vbox7.set_spacing(1)

		self.hbox6 = gtk.HBox(False, 0)
		self.hbox6.show()
		self.hbox6.set_spacing(5)

		self.QueryLabel = gtk.Label(_("Query"))
		self.QueryLabel.set_alignment(0, 0.50)
		self.QueryLabel.set_padding(3, 0)
		self.QueryLabel.set_line_wrap(True)
		self.QueryLabel.show()
		self.hbox6.pack_start(self.QueryLabel)

		self.filtersCheck = gtk.CheckButton()
		self.filtersCheck.set_label(_("Enable filters"))
		self.filtersCheck.show()
		self.filtersCheck.connect("toggled", self.OnToggleFilters)

		self.hbox6.pack_start(self.filtersCheck, False, True, 0)

		self.RememberCheckButton = gtk.CheckButton()
		self.tooltips.set_tip(self.RememberCheckButton, _("This search will be opened the next time you start Nicotine+ and will send out new search requests after a server-set intervals (usually around one hour)"))
		self.RememberCheckButton.set_label(_("Wish"))
		self.RememberCheckButton.show()
		self.RememberCheckButton.connect("toggled", self.OnToggleRemember)

		self.hbox6.pack_start(self.RememberCheckButton, False, False, 0)

		self.button2 = gtk.Button()
		self.tooltips.set_tip(self.button2, _("Stop new search results from being displayed"))
		self.button2.show()
		self.button2.connect("clicked", self.OnIgnore)

		self.alignment36 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment36.show()

		self.hbox56 = gtk.HBox(False, 0)
		self.hbox56.show()
		self.hbox56.set_spacing(2)

		self.image36 = gtk.Image()
		self.image36.set_from_stock(gtk.STOCK_STOP, 4)
		self.image36.show()
		self.hbox56.pack_start(self.image36, False, False, 0)

		self.label65 = gtk.Label(_("Ignore"))
		self.label65.show()
		self.hbox56.pack_start(self.label65, False, False, 0)

		self.alignment36.add(self.hbox56)

		self.button2.add(self.alignment36)

		self.hbox6.pack_start(self.button2, False, False, 0)

		self.button3 = gtk.Button()
		self.button3.show()
		self.button3.connect("clicked", self.OnClose)

		self.alignment35 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment35.show()

		self.hbox55 = gtk.HBox(False, 0)
		self.hbox55.show()
		self.hbox55.set_spacing(2)

		self.image35 = gtk.Image()
		self.image35.set_from_stock(gtk.STOCK_CLOSE, 4)
		self.image35.show()
		self.hbox55.pack_start(self.image35, False, False, 0)

		self.label64 = gtk.Label(_("Close"))
		self.label64.show()
		self.hbox55.pack_start(self.label64, False, False, 0)

		self.alignment35.add(self.hbox55)

		self.button3.add(self.alignment35)

		self.hbox6.pack_start(self.button3, False, False, 0)

		self.vbox7.pack_start(self.hbox6, False, True, 3)

		self.Filters = gtk.HBox(False, 0)
		self.Filters.set_spacing(2)

		self.label13 = gtk.Label(_("Filter in:"))
		self.label13.set_padding(3, 0)
		self.label13.show()
		self.Filters.pack_start(self.label13, False, False, 0)

		self.FilterIn_List = gtk.ListStore(gobject.TYPE_STRING)
		self.FilterIn = gtk.ComboBoxEntry()
		self.FilterIn.show()

		self.FilterInEntry = self.FilterIn.child
		self.tooltips.set_tip(self.FilterInEntry, _(". = any character, * = 0 or more of the proceeding character, | = seperator, [a-zA-Z] = any single latin character"))
		self.FilterInEntry.connect("activate", self.OnRefilter)

		self.FilterIn.set_model(self.FilterIn_List)
		self.FilterIn.set_text_column(0)
		self.Filters.pack_start(self.FilterIn)

		self.label14 = gtk.Label(_("Filter out:"))
		self.label14.show()
		self.Filters.pack_start(self.label14, False, False, 0)

		self.FilterOut_List = gtk.ListStore(gobject.TYPE_STRING)
		self.FilterOut = gtk.ComboBoxEntry()
		self.FilterOut.show()

		self.FilterOutEntry = self.FilterOut.child
		self.FilterOutEntry.connect("activate", self.OnRefilter)

		self.FilterOut.set_model(self.FilterOut_List)
		self.FilterOut.set_text_column(0)
		self.Filters.pack_start(self.FilterOut)

		self.label15 = gtk.Label(_("Size:"))
		self.label15.show()
		self.Filters.pack_start(self.label15, False, False, 0)

		self.FilterSize_List = gtk.ListStore(gobject.TYPE_STRING)
		self.FilterSize = gtk.ComboBoxEntry()
		self.FilterSize.set_size_request(75, -1)
		self.FilterSize.show()

		self.FilterSizeEntry = self.FilterSize.child
		self.FilterSizeEntry.connect("activate", self.OnRefilter)

		self.FilterSize.set_model(self.FilterSize_List)
		self.FilterSize.set_text_column(0)
		self.Filters.pack_start(self.FilterSize, False, True, 0)

		self.label16 = gtk.Label(_("Bitrate:"))
		self.label16.show()
		self.Filters.pack_start(self.label16, False, False, 0)

		self.FilterBitrate_List = gtk.ListStore(gobject.TYPE_STRING)
		self.FilterBitrate = gtk.ComboBoxEntry()
		self.FilterBitrate.set_size_request(75, -1)
		self.FilterBitrate.show()

		self.FilterBitrateEntry = self.FilterBitrate.child
		self.FilterBitrateEntry.connect("activate", self.OnRefilter)

		self.FilterBitrate.set_model(self.FilterBitrate_List)
		self.FilterBitrate.set_text_column(0)
		self.Filters.pack_start(self.FilterBitrate, False, True, 0)

		self.label23 = gtk.Label(_("Country:"))
		self.label23.show()
		self.Filters.pack_start(self.label23, False, False, 0)

		self.FilterCountry_List = gtk.ListStore(gobject.TYPE_STRING)
		self.FilterCountry = gtk.ComboBoxEntry()
		self.FilterCountry.set_size_request(75, -1)
		self.FilterCountry.show()

		self.FilterCountryEntry = self.FilterCountry.child
		self.FilterCountryEntry.connect("activate", self.OnRefilter)

		self.FilterCountry.set_model(self.FilterCountry_List)
		self.FilterCountry.set_text_column(0)
		self.Filters.pack_start(self.FilterCountry, False, True, 0)

		self.FilterFreeSlot = gtk.CheckButton()
		self.FilterFreeSlot.set_label(_("Free slot"))
		self.FilterFreeSlot.show()
		self.FilterFreeSlot.connect("toggled", self.OnRefilter)

		self.Filters.pack_start(self.FilterFreeSlot, False, False, 0)

		self.vbox7.pack_start(self.Filters, False, True, 3)

		self.scrolledwindow17 = gtk.ScrolledWindow()
		self.scrolledwindow17.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.scrolledwindow17.show()
		self.scrolledwindow17.set_shadow_type(gtk.SHADOW_IN)

		self.ResultsList = gtk.TreeView()
		self.ResultsList.show()
		self.scrolledwindow17.add(self.ResultsList)

		self.vbox7.pack_start(self.scrolledwindow17)


		if create:
			self.SearchTab.add(self.vbox7)

	def OnToggleFilters(self, widget):
		pass

	def OnToggleRemember(self, widget):
		pass

	def OnIgnore(self, widget):
		pass

	def OnClose(self, widget):
		pass

	def OnRefilter(self, widget):
		pass

	def get_custom_widget(self, id, string1, string2, int1, int2):
		w = gtk.Label(_("(custom widget: %s)") % id)
		return w

class UserInfoTab:
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
			self.UserInfoTab = gtk.Window()
			self.UserInfoTab.set_title(_("window1"))
			self.UserInfoTab.add_accel_group(self.accel_group)
			self.UserInfoTab.show()

		self.Main = gtk.HBox(False, 0)
		self.Main.show()

		self.hpaned5 = gtk.HPaned()
		self.hpaned5.show()

		self.InfoVbox = gtk.VBox(False, 0)
		self.InfoVbox.set_size_request(250, -1)
		self.InfoVbox.show()

		self.DescriptionExpander = gtk.Expander()
		self.DescriptionExpander.set_expanded(True)
		self.DescriptionExpander.show()

		self.frame1 = gtk.Frame()
		self.frame1.show()

		self.vbox16 = gtk.VBox(False, 0)
		self.vbox16.show()

		self.Encoding_List = gtk.ListStore(gobject.TYPE_STRING)
		self.Encoding = gtk.ComboBox()
		self.Encoding.show()
		self.Encoding.connect("changed", self.OnEncodingChanged)

		self.Encoding.set_model(self.Encoding_List)
		cell = gtk.CellRendererText()
		self.Encoding.pack_start(cell, True)
		self.Encoding.add_attribute(cell, 'text', 0)
		self.vbox16.pack_start(self.Encoding, False, False, 0)

		self.scrolledwindow28 = gtk.ScrolledWindow()
		self.scrolledwindow28.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.scrolledwindow28.show()
		self.scrolledwindow28.set_shadow_type(gtk.SHADOW_IN)

		self.descr = gtk.TextView()
		self.descr.set_wrap_mode(gtk.WRAP_WORD)
		self.descr.set_cursor_visible(False)
		self.descr.set_editable(False)
		self.descr.show()
		self.scrolledwindow28.add(self.descr)

		self.vbox16.pack_start(self.scrolledwindow28)

		self.frame1.add(self.vbox16)

		self.DescriptionExpander.add(self.frame1)

		self.label74 = gtk.Label(_("Self description:"))
		self.label74.show()
		self.DescriptionExpander.set_label_widget(self.label74)

		self.InfoVbox.pack_start(self.DescriptionExpander)

		self.InformationExpander = gtk.Expander()
		self.InformationExpander.set_expanded(True)
		self.InformationExpander.show()

		self.frame2 = gtk.Frame()
		self.frame2.show()

		self.vbox10 = gtk.VBox(False, 0)
		self.vbox10.show()
		self.vbox10.set_spacing(5)
		self.vbox10.set_border_width(5)

		self.uploads = gtk.Label(_("Total uploads allowed: unknown"))
		self.uploads.set_alignment(0, 0.50)
		self.uploads.show()
		self.vbox10.pack_start(self.uploads, False, False, 0)

		self.slotsavail = gtk.Label(_("Slots free: unknown"))
		self.slotsavail.set_alignment(0, 0.50)
		self.slotsavail.show()
		self.vbox10.pack_start(self.slotsavail, False, False, 0)

		self.hbox65 = gtk.HBox(False, 0)
		self.hbox65.show()
		self.hbox65.set_spacing(5)

		self.queuesize = gtk.Label(_("Queue size: unknown"))
		self.queuesize.set_alignment(0, 0.50)
		self.queuesize.show()
		self.hbox65.pack_start(self.queuesize, False, False, 0)

		self.vbox10.pack_start(self.hbox65, False, False, 0)

		self.hbox17 = gtk.HBox(False, 0)
		self.hbox17.show()
		self.hbox17.set_spacing(5)

		self.speed = gtk.Label(_("Speed: unknown"))
		self.speed.set_alignment(0, 0.50)
		self.speed.show()
		self.hbox17.pack_start(self.speed, False, False, 0)

		self.vbox10.pack_start(self.hbox17, False, False, 0)

		self.hbox16 = gtk.HBox(False, 0)
		self.hbox16.show()
		self.hbox16.set_spacing(5)

		self.filesshared = gtk.Label(_("Files: unknown"))
		self.filesshared.set_alignment(0, 0.50)
		self.filesshared.show()
		self.hbox16.pack_start(self.filesshared, False, False, 0)

		self.dirsshared = gtk.Label(_("Directories: unknown"))
		self.dirsshared.set_alignment(0, 0.50)
		self.dirsshared.show()
		self.hbox16.pack_start(self.dirsshared, False, False, 0)

		self.vbox10.pack_start(self.hbox16, False, False, 0)

		self.hbox66 = gtk.HBox(False, 0)
		self.hbox66.show()
		self.hbox66.set_spacing(5)

		self.label72 = gtk.Label(_("Accepts Uploads from:"))
		self.label72.show()
		self.hbox66.pack_start(self.label72, False, False, 0)

		self.AcceptUploads = gtk.Label(_("unknown"))
		self.AcceptUploads.show()
		self.hbox66.pack_start(self.AcceptUploads, False, False, 0)

		self.vbox10.pack_start(self.hbox66, False, True, 0)

		self.progressbar = gtk.ProgressBar()
		self.progressbar.show()
		self.vbox10.pack_end(self.progressbar, False, False, 0)

		self.frame2.add(self.vbox10)

		self.InformationExpander.add(self.frame2)

		self.label72 = gtk.Label(_("Information:"))
		self.label72.show()
		self.InformationExpander.set_label_widget(self.label72)

		self.InfoVbox.pack_start(self.InformationExpander)

		self.InterestsExpander = gtk.Expander()
		self.InterestsExpander.show()

		self.vbox18 = gtk.VBox(False, 0)
		self.vbox18.show()

		self.scrolledwindow31 = gtk.ScrolledWindow()
		self.scrolledwindow31.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.scrolledwindow31.show()
		self.scrolledwindow31.set_shadow_type(gtk.SHADOW_IN)

		self.Likes = gtk.TreeView()
		self.Likes.show()
		self.scrolledwindow31.add(self.Likes)

		self.vbox18.pack_start(self.scrolledwindow31)

		self.scrolledwindow32 = gtk.ScrolledWindow()
		self.scrolledwindow32.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.scrolledwindow32.show()
		self.scrolledwindow32.set_shadow_type(gtk.SHADOW_IN)

		self.Hates = gtk.TreeView()
		self.Hates.show()
		self.scrolledwindow32.add(self.Hates)

		self.vbox18.pack_start(self.scrolledwindow32)

		self.InterestsExpander.add(self.vbox18)

		self.label73 = gtk.Label(_("Interests:"))
		self.label73.show()
		self.InterestsExpander.set_label_widget(self.label73)

		self.InfoVbox.pack_start(self.InterestsExpander, False, True, 0)

		self.hpaned5.pack1(self.InfoVbox, False, True)

		self.frame3 = gtk.Frame()
		self.frame3.show()

		self.scrolledwindow19 = gtk.ScrolledWindow()
		self.scrolledwindow19.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.scrolledwindow19.show()

		self.viewport2 = gtk.Viewport()
		self.viewport2.show()
		self.viewport2.set_shadow_type(gtk.SHADOW_NONE)

		self.eventbox1 = gtk.EventBox()
		self.eventbox1.show()
		self.eventbox1.connect("scroll_event", self.OnScrollEvent)

		self.image = gtk.Image()
		self.image.set_from_stock(gtk.STOCK_MISSING_IMAGE, 4)
		self.image.show()
		self.eventbox1.add(self.image)

		self.viewport2.add(self.eventbox1)

		self.scrolledwindow19.add(self.viewport2)

		self.frame3.add(self.scrolledwindow19)

		self.label19 = gtk.Label(_("Picture:"))
		self.label19.show()
		self.frame3.set_label_widget(self.label19)

		self.hpaned5.pack2(self.frame3, True, True)

		self.Main.pack_start(self.hpaned5)

		self.vbox9 = gtk.VBox(False, 0)
		self.vbox9.show()
		self.vbox9.set_spacing(5)
		self.vbox9.set_border_width(5)

		self.button4 = gtk.Button()
		self.button4.show()
		self.button4.connect("clicked", self.OnSendMessage)

		self.alignment23 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment23.show()

		self.hbox43 = gtk.HBox(False, 0)
		self.hbox43.show()
		self.hbox43.set_spacing(2)

		self.image23 = gtk.Image()
		self.image23.set_from_stock(gtk.STOCK_EDIT, 4)
		self.image23.show()
		self.hbox43.pack_start(self.image23, False, False, 0)

		self.label52 = gtk.Label(_("Private chat"))
		self.label52.show()
		self.hbox43.pack_start(self.label52, False, False, 0)

		self.alignment23.add(self.hbox43)

		self.button4.add(self.alignment23)

		self.vbox9.pack_start(self.button4, False, False, 0)

		self.button5 = gtk.Button()
		self.button5.show()
		self.button5.connect("clicked", self.OnBrowseUser)

		self.alignment24 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment24.show()

		self.hbox44 = gtk.HBox(False, 0)
		self.hbox44.show()
		self.hbox44.set_spacing(2)

		self.image24 = gtk.Image()
		self.image24.set_from_stock(gtk.STOCK_HARDDISK, 4)
		self.image24.show()
		self.hbox44.pack_start(self.image24, False, False, 0)

		self.label53 = gtk.Label(_("Browse"))
		self.label53.show()
		self.hbox44.pack_start(self.label53, False, False, 0)

		self.alignment24.add(self.hbox44)

		self.button5.add(self.alignment24)

		self.vbox9.pack_start(self.button5, False, False, 0)

		self.button6 = gtk.Button()
		self.button6.show()
		self.button6.connect("clicked", self.OnShowIPaddress)

		self.alignment25 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment25.show()

		self.hbox45 = gtk.HBox(False, 0)
		self.hbox45.show()
		self.hbox45.set_spacing(2)

		self.image25 = gtk.Image()
		self.image25.set_from_stock(gtk.STOCK_NETWORK, 4)
		self.image25.show()
		self.hbox45.pack_start(self.image25, False, False, 0)

		self.label54 = gtk.Label(_("Show IP"))
		self.label54.show()
		self.hbox45.pack_start(self.label54, False, False, 0)

		self.alignment25.add(self.hbox45)

		self.button6.add(self.alignment25)

		self.vbox9.pack_start(self.button6, False, False, 0)

		self.AddToList = gtk.Button()
		self.AddToList.show()
		self.AddToList.connect("clicked", self.OnAddToList)

		self.alignment26 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment26.show()

		self.hbox46 = gtk.HBox(False, 0)
		self.hbox46.show()
		self.hbox46.set_spacing(2)

		self.image26 = gtk.Image()
		self.image26.set_from_stock(gtk.STOCK_ADD, 4)
		self.image26.show()
		self.hbox46.pack_start(self.image26, False, False, 0)

		self.label55 = gtk.Label(_("Add to list"))
		self.label55.show()
		self.hbox46.pack_start(self.label55, False, False, 0)

		self.alignment26.add(self.hbox46)

		self.AddToList.add(self.alignment26)

		self.vbox9.pack_start(self.AddToList, False, False, 0)

		self.BanUser = gtk.Button()
		self.BanUser.show()
		self.BanUser.connect("clicked", self.OnBanUser)

		self.alignment37 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment37.show()

		self.hbox57 = gtk.HBox(False, 0)
		self.hbox57.show()
		self.hbox57.set_spacing(2)

		self.image37 = gtk.Image()
		self.image37.set_from_stock(gtk.STOCK_STOP, 4)
		self.image37.show()
		self.hbox57.pack_start(self.image37, False, False, 0)

		self.label66 = gtk.Label(_("Ban"))
		self.label66.show()
		self.hbox57.pack_start(self.label66, False, False, 0)

		self.alignment37.add(self.hbox57)

		self.BanUser.add(self.alignment37)

		self.vbox9.pack_start(self.BanUser, False, False, 0)

		self.IgnoreUser = gtk.Button()
		self.IgnoreUser.show()
		self.IgnoreUser.connect("clicked", self.OnIgnoreUser)

		self.alignment32 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment32.show()

		self.hbox52 = gtk.HBox(False, 0)
		self.hbox52.show()
		self.hbox52.set_spacing(2)

		self.image32 = gtk.Image()
		self.image32.set_from_stock(gtk.STOCK_DELETE, 4)
		self.image32.show()
		self.hbox52.pack_start(self.image32, False, False, 0)

		self.label61 = gtk.Label(_("Ignore"))
		self.label61.show()
		self.hbox52.pack_start(self.label61, False, False, 0)

		self.alignment32.add(self.hbox52)

		self.IgnoreUser.add(self.alignment32)

		self.vbox9.pack_start(self.IgnoreUser, False, False, 0)

		self.SavePicture = gtk.Button()
		self.SavePicture.show()
		self.SavePicture.connect("clicked", self.OnSavePicture)

		self.alignment29 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment29.show()

		self.hbox49 = gtk.HBox(False, 0)
		self.hbox49.show()
		self.hbox49.set_spacing(2)

		self.image29 = gtk.Image()
		self.image29.set_from_stock(gtk.STOCK_SAVE, 4)
		self.image29.show()
		self.hbox49.pack_start(self.image29, False, False, 0)

		self.label58 = gtk.Label(_("Save pic"))
		self.label58.show()
		self.hbox49.pack_start(self.label58, False, False, 0)

		self.alignment29.add(self.hbox49)

		self.SavePicture.add(self.alignment29)

		self.vbox9.pack_start(self.SavePicture, False, False, 0)

		self.Filler = gtk.Label()
		self.Filler.show()
		self.vbox9.pack_start(self.Filler)

		self.RefreshUserinfo = gtk.Button()
		self.RefreshUserinfo.show()
		self.RefreshUserinfo.connect("clicked", self.OnRefresh)

		self.alignment30 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment30.show()

		self.hbox50 = gtk.HBox(False, 0)
		self.hbox50.show()
		self.hbox50.set_spacing(2)

		self.image30 = gtk.Image()
		self.image30.set_from_stock(gtk.STOCK_REFRESH, 4)
		self.image30.show()
		self.hbox50.pack_start(self.image30, False, False, 0)

		self.label59 = gtk.Label(_("Refresh"))
		self.label59.show()
		self.hbox50.pack_start(self.label59, False, False, 0)

		self.alignment30.add(self.hbox50)

		self.RefreshUserinfo.add(self.alignment30)

		self.vbox9.pack_start(self.RefreshUserinfo, False, False, 0)

		self.CloseUserinfo = gtk.Button()
		self.CloseUserinfo.show()
		self.CloseUserinfo.connect("clicked", self.OnClose)

		self.alignment31 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment31.show()

		self.hbox51 = gtk.HBox(False, 0)
		self.hbox51.show()
		self.hbox51.set_spacing(2)

		self.image31 = gtk.Image()
		self.image31.set_from_stock(gtk.STOCK_CLOSE, 4)
		self.image31.show()
		self.hbox51.pack_start(self.image31, False, False, 0)

		self.label60 = gtk.Label(_("Close"))
		self.label60.show()
		self.hbox51.pack_start(self.label60, False, False, 0)

		self.alignment31.add(self.hbox51)

		self.CloseUserinfo.add(self.alignment31)

		self.vbox9.pack_start(self.CloseUserinfo, False, False, 0)

		self.Main.pack_start(self.vbox9, False, True, 0)


		if create:
			self.UserInfoTab.add(self.Main)

	def OnEncodingChanged(self, widget):
		pass

	def OnScrollEvent(self, widget):
		pass

	def OnSendMessage(self, widget):
		pass

	def OnBrowseUser(self, widget):
		pass

	def OnShowIPaddress(self, widget):
		pass

	def OnAddToList(self, widget):
		pass

	def OnBanUser(self, widget):
		pass

	def OnIgnoreUser(self, widget):
		pass

	def OnSavePicture(self, widget):
		pass

	def OnRefresh(self, widget):
		pass

	def OnClose(self, widget):
		pass

	def get_custom_widget(self, id, string1, string2, int1, int2):
		w = gtk.Label(_("(custom widget: %s)") % id)
		return w

class UserBrowseTab:
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
			self.UserBrowseTab = gtk.Window()
			self.UserBrowseTab.set_title(_("window1"))
			self.UserBrowseTab.add_accel_group(self.accel_group)
			self.UserBrowseTab.show()

		self.Main = gtk.VBox(False, 0)
		self.Main.show()

		self.hbox8 = gtk.HBox(False, 0)
		self.hbox8.show()
		self.hbox8.set_spacing(5)

		self.label20 = gtk.Label(_("Search file and folder names (exact match):"))
		self.label20.show()
		self.hbox8.pack_start(self.label20, False, False, 5)

		self.entry4 = gtk.Entry()
		self.entry4.show()
		self.entry4.connect("activate", self.OnSearch)
		self.hbox8.pack_start(self.entry4)

		self.Encoding_List = gtk.ListStore(gobject.TYPE_STRING)
		self.Encoding = gtk.ComboBox()
		self.Encoding.show()
		self.Encoding.connect("changed", self.OnEncodingChanged)

		self.Encoding.set_model(self.Encoding_List)
		cell = gtk.CellRendererText()
		self.Encoding.pack_start(cell, True)
		self.Encoding.add_attribute(cell, 'text', 0)
		self.hbox8.pack_start(self.Encoding, False, False, 5)

		self.Main.pack_start(self.hbox8, False, True, 0)

		self.hpaned2 = gtk.HPaned()
		self.hpaned2.show()

		self.vbox17 = gtk.VBox(False, 0)
		self.vbox17.show()

		self.hbox61 = gtk.HBox(False, 0)
		self.hbox61.show()

		self.ExpandButton = gtk.ToggleButton()
		self.ExpandButton.set_label(_("Expand / Collapse all"))
		self.ExpandButton.show()
		self.ExpandButton.connect("clicked", self.OnExpand)

		self.hbox61.pack_start(self.ExpandButton, False, False, 0)

		self.vbox17.pack_start(self.hbox61, False, False, 0)

		self.scrolledwindow21 = gtk.ScrolledWindow()
		self.scrolledwindow21.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.scrolledwindow21.set_size_request(250, -1)
		self.scrolledwindow21.show()
		self.scrolledwindow21.set_shadow_type(gtk.SHADOW_IN)

		self.FolderTreeView = gtk.TreeView()
		self.FolderTreeView.show()
		self.FolderTreeView.set_headers_visible(False)
		self.scrolledwindow21.add(self.FolderTreeView)

		self.vbox17.pack_start(self.scrolledwindow21)

		self.hpaned2.pack1(self.vbox17, False, True)

		self.sMain = gtk.VBox(False, 0)
		self.sMain.show()

		self.hbox9 = gtk.HBox(False, 0)
		self.hbox9.show()
		self.hbox9.set_spacing(5)
		self.hbox9.set_border_width(10)

		self.progressbar1 = gtk.ProgressBar()
		self.progressbar1.set_size_request(250, -1)
		self.progressbar1.show()
		self.hbox9.pack_start(self.progressbar1)

		self.SaveButton = gtk.Button()
		self.SaveButton.show()
		self.SaveButton.connect("clicked", self.OnSave)

		self.alignment41 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment41.show()

		self.hbox63 = gtk.HBox(False, 0)
		self.hbox63.show()
		self.hbox63.set_spacing(2)

		self.image365 = gtk.Image()
		self.image365.set_from_stock(gtk.STOCK_SAVE, 4)
		self.image365.show()
		self.hbox63.pack_start(self.image365, False, False, 0)

		self.label70 = gtk.Label(_("Save"))
		self.label70.show()
		self.hbox63.pack_start(self.label70, False, False, 0)

		self.alignment41.add(self.hbox63)

		self.SaveButton.add(self.alignment41)

		self.hbox9.pack_start(self.SaveButton, False, False, 0)

		self.RefreshButton = gtk.Button()
		self.RefreshButton.show()
		self.RefreshButton.connect("clicked", self.OnRefresh)

		self.alignment42 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment42.show()

		self.hbox64 = gtk.HBox(False, 0)
		self.hbox64.show()
		self.hbox64.set_spacing(2)

		self.image366 = gtk.Image()
		self.image366.set_from_stock(gtk.STOCK_REFRESH, 4)
		self.image366.show()
		self.hbox64.pack_start(self.image366, False, False, 0)

		self.label71 = gtk.Label(_("Refresh"))
		self.label71.show()
		self.hbox64.pack_start(self.label71, False, False, 0)

		self.alignment42.add(self.hbox64)

		self.RefreshButton.add(self.alignment42)

		self.hbox9.pack_start(self.RefreshButton, False, False, 0)

		self.CloseButton = gtk.Button()
		self.CloseButton.show()
		self.CloseButton.connect("clicked", self.OnClose)

		self.alignment40 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment40.show()

		self.hbox62 = gtk.HBox(False, 0)
		self.hbox62.show()
		self.hbox62.set_spacing(2)

		self.image364 = gtk.Image()
		self.image364.set_from_stock(gtk.STOCK_CLOSE, 4)
		self.image364.show()
		self.hbox62.pack_start(self.image364, False, False, 0)

		self.label69 = gtk.Label(_("Close"))
		self.label69.show()
		self.hbox62.pack_start(self.label69, False, False, 0)

		self.alignment40.add(self.hbox62)

		self.CloseButton.add(self.alignment40)

		self.hbox9.pack_start(self.CloseButton, False, False, 0)

		self.sMain.pack_start(self.hbox9, False, True, 0)

		self.scrolledwindow20 = gtk.ScrolledWindow()
		self.scrolledwindow20.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.scrolledwindow20.show()
		self.scrolledwindow20.set_shadow_type(gtk.SHADOW_IN)

		self.FileTreeView = gtk.TreeView()
		self.FileTreeView.show()
		self.scrolledwindow20.add(self.FileTreeView)

		self.sMain.pack_start(self.scrolledwindow20)

		self.hpaned2.pack2(self.sMain, True, True)

		self.Main.pack_start(self.hpaned2)


		if create:
			self.UserBrowseTab.add(self.Main)

	def OnSearch(self, widget):
		pass

	def OnEncodingChanged(self, widget):
		pass

	def OnExpand(self, widget):
		pass

	def OnSave(self, widget):
		pass

	def OnRefresh(self, widget):
		pass

	def OnClose(self, widget):
		pass

	def get_custom_widget(self, id, string1, string2, int1, int2):
		w = gtk.Label(_("(custom widget: %s)") % id)
		return w

class RoomList:
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
			self.RoomList = gtk.Window()
			self.RoomList.set_title(_("window1"))
			self.RoomList.add_accel_group(self.accel_group)
			self.RoomList.show()

		self.vbox2 = gtk.VBox(False, 0)
		self.vbox2.show()

		self.scrolledwindow10 = gtk.ScrolledWindow()
		self.scrolledwindow10.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.scrolledwindow10.show()
		self.scrolledwindow10.set_shadow_type(gtk.SHADOW_IN)

		self.RoomsList = gtk.TreeView()
		self.RoomsList.show()
		self.scrolledwindow10.add(self.RoomsList)

		self.vbox2.pack_start(self.scrolledwindow10)

		self.hbox1 = gtk.HBox(False, 0)
		self.hbox1.show()
		self.hbox1.set_spacing(5)
		self.hbox1.set_border_width(3)

		self.label10 = gtk.Label(_("Create: "))
		self.label10.show()
		self.hbox1.pack_start(self.label10, False, False, 0)

		self.CreateRoomEntry = gtk.Entry()
		self.CreateRoomEntry.show()
		self.CreateRoomEntry.connect("activate", self.OnCreateRoom)
		self.hbox1.pack_start(self.CreateRoomEntry)

		self.HideRoomList = gtk.Button()
		self.HideRoomList.show()

		self.alignment27 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment27.show()

		self.hbox27 = gtk.HBox(False, 0)
		self.hbox27.show()
		self.hbox27.set_spacing(2)

		self.image7 = gtk.Image()
		self.image7.set_from_stock(gtk.STOCK_REMOVE, 4)
		self.image7.show()
		self.hbox27.pack_start(self.image7, False, True, 0)

		self.JumpLabel = gtk.Label(_("Hide list"))
		self.JumpLabel.show()
		self.hbox27.pack_start(self.JumpLabel)

		self.alignment27.add(self.hbox27)

		self.HideRoomList.add(self.alignment27)

		self.hbox1.pack_start(self.HideRoomList, False, True, 0)

		self.vbox2.pack_start(self.hbox1, False, True, 0)


		if create:
			self.RoomList.add(self.vbox2)

	def OnCreateRoom(self, widget):
		pass

	def get_custom_widget(self, id, string1, string2, int1, int2):
		w = gtk.Label(_("(custom widget: %s)") % id)
		return w

