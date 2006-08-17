import gtk, gobject
from pynicotine.utils import _

class MainWindow:
    def __init__(self, create = True, accel_group = None):
        if accel_group is None:
             self.accel_group = gtk.AccelGroup()
        else:
             self.accel_group = accel_group
        if create:
            self.MainWindow = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.MainWindow.set_default_size(800, 600)
            self.MainWindow.set_title(_("Nicotine"))
            self.MainWindow.set_position(gtk.WIN_POS_CENTER)
            self.MainWindow.add_accel_group(self.accel_group)
            self.MainWindow.show()
            self.MainWindow.connect("selection_get", self.OnSelectionGet)
            self.MainWindow.connect("focus_in_event", self.OnFocusIn)
            self.MainWindow.connect("focus_out_event", self.OnFocusOut)

        self.vbox1 = gtk.VBox(False, 0)
        self.vbox1.show()
        self.vbox1.set_spacing(0)

        self.menubar1 = gtk.MenuBar()
        self.menubar1.show()

        self.file1 = gtk.MenuItem(_("_File"))
        self.file1.show()

        self.file1_menu = gtk.Menu()

        self.connect1 = gtk.MenuItem(_("_Connect"))
        self.connect1.show()
        self.connect1.connect("activate", self.OnConnect)
        self.connect1.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("c"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

        self.file1_menu.append(self.connect1)

        self.disconnect1 = gtk.MenuItem(_("_Disconnect"))
        self.disconnect1.show()
        self.disconnect1.connect("activate", self.OnDisconnect)
        self.disconnect1.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("d"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

        self.file1_menu.append(self.disconnect1)

        self.awayreturn1 = gtk.MenuItem(_("_Away/Return"))
        self.awayreturn1.show()
        self.awayreturn1.connect("activate", self.OnAway)
        self.awayreturn1.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("a"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

        self.file1_menu.append(self.awayreturn1)

        self.check_privileges1 = gtk.MenuItem(_("Check _privileges"))
        self.check_privileges1.show()
        self.check_privileges1.connect("activate", self.OnCheckPrivileges)

        self.file1_menu.append(self.check_privileges1)

        self.scheidingslijn1 = gtk.MenuItem()
        self.scheidingslijn1.show()

        self.file1_menu.append(self.scheidingslijn1)

        self.show_debug_info1 = gtk.CheckMenuItem(_("Show _debug info"))
        self.show_debug_info1.set_active(False)
        self.show_debug_info1.show()
        self.show_debug_info1.connect("activate", self.OnShowDebug)

        self.file1_menu.append(self.show_debug_info1)

        self.scheidingslijn8 = gtk.MenuItem()
        self.scheidingslijn8.show()

        self.file1_menu.append(self.scheidingslijn8)

        self.hide_log_window1 = gtk.CheckMenuItem(_("_Hide log window"))
        self.hide_log_window1.set_active(False)
        self.hide_log_window1.show()
        self.hide_log_window1.connect("activate", self.OnHideLog)
        self.hide_log_window1.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("h"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

        self.file1_menu.append(self.hide_log_window1)

        self.hide_room_list1 = gtk.CheckMenuItem(_("Hide room _list"))
        self.hide_room_list1.set_active(False)
        self.hide_room_list1.show()
        self.hide_room_list1.connect("activate", self.OnHideRoomList)
        self.hide_room_list1.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("r"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

        self.file1_menu.append(self.hide_room_list1)

        self.hide_tickers1 = gtk.CheckMenuItem(_("Hide _tickers"))
        self.hide_tickers1.set_active(False)
        self.hide_tickers1.show()
        self.hide_tickers1.connect("activate", self.OnHideTickers)
        self.hide_tickers1.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("t"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

        self.file1_menu.append(self.hide_tickers1)

        self.buddylist_in_chatrooms1 = gtk.CheckMenuItem(_("Buddylist in Chatrooms"))
        self.buddylist_in_chatrooms1.set_active(False)
        self.buddylist_in_chatrooms1.show()
        self.buddylist_in_chatrooms1.connect("activate", self.OnToggleBuddyList)
        self.buddylist_in_chatrooms1.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("u"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

        self.file1_menu.append(self.buddylist_in_chatrooms1)

        self.scheidingslijn5 = gtk.MenuItem()
        self.scheidingslijn5.show()

        self.file1_menu.append(self.scheidingslijn5)

        self.settings1 = gtk.MenuItem(_("_Settings"))
        self.settings1.show()
        self.settings1.connect("activate", self.OnSettings)

        self.file1_menu.append(self.settings1)

        self.scheidingslijn6 = gtk.MenuItem()
        self.scheidingslijn6.show()

        self.file1_menu.append(self.scheidingslijn6)

        self.rescan1 = gtk.MenuItem(_("_Rescan shares"))
        self.rescan1.show()
        self.rescan1.connect("activate", self.OnRescan)

        self.file1_menu.append(self.rescan1)

        self.rescan2 = gtk.MenuItem(_("_Rescan Buddy shares"))
        self.rescan2.show()
        self.rescan2.connect("activate", self.OnBuddyRescan)

        self.file1_menu.append(self.rescan2)

        self.browse_my_shares1 = gtk.MenuItem(_("_Browse my shares"))
        self.browse_my_shares1.show()
        self.browse_my_shares1.connect("activate", self.OnBrowseMyShares)

        self.file1_menu.append(self.browse_my_shares1)

        self.scheidingslijn2 = gtk.MenuItem()
        self.scheidingslijn2.show()

        self.file1_menu.append(self.scheidingslijn2)

        self.exit1 = gtk.MenuItem(_("E_xit"))
        self.exit1.show()
        self.exit1.connect("activate", self.OnExit)
        self.exit1.add_accelerator("activate", self.accel_group, gtk.gdk.keyval_from_name("x"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

        self.file1_menu.append(self.exit1)

        self.file1.set_submenu(self.file1_menu)

        self.menubar1.append(self.file1)

        self.modes1 = gtk.MenuItem(_("_Modes"))
        self.modes1.show()

        self.modes1_menu = gtk.Menu()

        self.chat_rooms1 = gtk.MenuItem(_("_Chat Rooms"))
        self.chat_rooms1.show()
        self.chat_rooms1.connect("activate", self.OnChatRooms)

        self.modes1_menu.append(self.chat_rooms1)

        self.private_chat1 = gtk.MenuItem(_("_Private Chat"))
        self.private_chat1.show()
        self.private_chat1.connect("activate", self.OnPrivateChat)

        self.modes1_menu.append(self.private_chat1)

        self.downloads1 = gtk.MenuItem(_("_Downloads"))
        self.downloads1.show()
        self.downloads1.connect("activate", self.OnDownloads)

        self.modes1_menu.append(self.downloads1)

        self.uploads1 = gtk.MenuItem(_("_Uploads"))
        self.uploads1.show()
        self.uploads1.connect("activate", self.OnUploads)

        self.modes1_menu.append(self.uploads1)

        self.search_files1 = gtk.MenuItem(_("_Search Files"))
        self.search_files1.show()
        self.search_files1.connect("activate", self.OnSearchFiles)

        self.modes1_menu.append(self.search_files1)

        self.user_info1 = gtk.MenuItem(_("User I_nfo"))
        self.user_info1.show()
        self.user_info1.connect("activate", self.OnUserInfo)

        self.modes1_menu.append(self.user_info1)

        self.user_browse1 = gtk.MenuItem(_("User _Browse"))
        self.user_browse1.show()
        self.user_browse1.connect("activate", self.OnUserBrowse)

        self.modes1_menu.append(self.user_browse1)

        self.interests1 = gtk.MenuItem(_("_Interests"))
        self.interests1.show()
        self.interests1.connect("activate", self.OnInterests)

        self.modes1_menu.append(self.interests1)

        self.user_list1 = gtk.MenuItem(_("Buddy _List"))
        self.user_list1.show()
        self.user_list1.connect("activate", self.OnUserList)

        self.modes1_menu.append(self.user_list1)

        self.modes1.set_submenu(self.modes1_menu)

        self.menubar1.append(self.modes1)

        self.help1 = gtk.MenuItem(_("H_elp"))
        self.help1.show()

        self.help1_menu = gtk.Menu()

        self.about_chatroom_commands1 = gtk.MenuItem(_("About _chat room commands"))
        self.about_chatroom_commands1.show()
        self.about_chatroom_commands1.connect("activate", self.OnAboutChatroomCommands)

        self.help1_menu.append(self.about_chatroom_commands1)

        self.about_private_chat_command1 = gtk.MenuItem(_("About _private chat commands"))
        self.about_private_chat_command1.show()
        self.about_private_chat_command1.connect("activate", self.OnAboutPrivateChatCommands)

        self.help1_menu.append(self.about_private_chat_command1)

        self.scheidingslijn4 = gtk.MenuItem()
        self.scheidingslijn4.show()

        self.help1_menu.append(self.scheidingslijn4)

        self.abour_search_filters1 = gtk.MenuItem(_("About _search filters"))
        self.abour_search_filters1.show()
        self.abour_search_filters1.connect("activate", self.OnAboutFilters)

        self.help1_menu.append(self.abour_search_filters1)

        self.scheidingslijn3 = gtk.MenuItem()
        self.scheidingslijn3.show()

        self.help1_menu.append(self.scheidingslijn3)

        self.check_latest1 = gtk.MenuItem(_("Check _latest"))
        self.check_latest1.show()
        self.check_latest1.connect("activate", self.OnCheckLatest)

        self.help1_menu.append(self.check_latest1)

        self.scheidingslijn7 = gtk.MenuItem()
        self.scheidingslijn7.show()

        self.help1_menu.append(self.scheidingslijn7)

        self.about_nicotine1 = gtk.MenuItem(_("About _Nicotine"))
        self.about_nicotine1.show()
        self.about_nicotine1.connect("activate", self.OnAbout)

        self.help1_menu.append(self.about_nicotine1)

        self.help1.set_submenu(self.help1_menu)

        self.menubar1.append(self.help1)

        self.vbox1.pack_start(self.menubar1, False, False, 0)

        self.vpaned1 = gtk.VPaned()
        self.vpaned1.show()

        self.notebook1 = gtk.Notebook()
        self.notebook1.set_size_request(0, 0)
        self.notebook1.set_tab_pos(gtk.POS_TOP)
        self.notebook1.set_scrollable(True)
        self.notebook1.show()
        self.notebook1.connect("switch_page", self.OnSwitchPage)

        self.hpaned1 = gtk.HPaned()
        self.hpaned1.show()

        self.ChatNotebook = self.get_custom_widget("ChatNotebook", "", "", 0, 0)
        self.ChatNotebook.show()
        self.hpaned1.pack1(self.ChatNotebook, True, True)

        self.vpaned3 = gtk.VPaned()
        self.vpaned3.show()

        self.hpaned1.pack2(self.vpaned3, False, True)

        self.ChatTabLabel = self.get_custom_widget("ChatTabLabel", _("ImageLabel"), _("Chat rooms"), 0, 0)
        self.ChatTabLabel.show()
        self.privatevbox = gtk.VBox(False, 0)
        self.privatevbox.show()
        self.privatevbox.set_spacing(0)

        self.PrivatechatNotebook = self.get_custom_widget("PrivatechatNotebook", "", "", 0, 0)
        self.PrivatechatNotebook.show()
        self.privatevbox.pack_start(self.PrivatechatNotebook, True, True, 0)

        self.hbox20 = gtk.HBox(False, 5)
        self.hbox20.show()
        self.hbox20.set_spacing(5)
        self.hbox20.set_border_width(5)

        self.sPrivateChatButton = gtk.Button()
        self.sPrivateChatButton.show()

        self.alignment10 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment10.show()

        self.hbox30 = gtk.HBox(False, 2)
        self.hbox30.show()
        self.hbox30.set_spacing(2)

        self.image10 = gtk.Image()
        self.image10.set_padding(0, 0)
        self.image10.set_from_stock(gtk.STOCK_JUMP_TO, 4)
        self.image10.show()
        self.hbox30.pack_start(self.image10, False, False, 0)

        self.label39 = gtk.Label(_("Start Message"))
        self.label39.set_padding(0, 0)
        self.label39.show()
        self.hbox30.pack_start(self.label39, False, False, 0)

        self.alignment10.add(self.hbox30)

        self.sPrivateChatButton.add(self.alignment10)

        self.hbox20.pack_end(self.sPrivateChatButton, False, False, 0)

        self.PrivateChatEntry = gtk.Entry()
        self.PrivateChatEntry.set_text("")
        self.PrivateChatEntry.set_editable(True)
        self.PrivateChatEntry.show()
        self.PrivateChatEntry.set_visibility(True)
        self.hbox20.pack_end(self.PrivateChatEntry, False, True, 0)

        self.label29 = gtk.Label(_("Input a user:"))
        self.label29.set_padding(0, 0)
        self.label29.show()
        self.hbox20.pack_end(self.label29, False, False, 0)

        self.privatevbox.pack_start(self.hbox20, False, True, 0)

        self.PrivateChatTabLabel = self.get_custom_widget("PrivateChatTabLabel", _("ImageLabel"), _("Private chat"), 0, 0)
        self.PrivateChatTabLabel.show()
        self.vboxdownloads = gtk.VBox(False, 0)
        self.vboxdownloads.show()
        self.vboxdownloads.set_spacing(0)

        self.scrolledwindow29 = gtk.ScrolledWindow()
        self.scrolledwindow29.set_policy(gtk.POLICY_ALWAYS, gtk.POLICY_ALWAYS)
        self.scrolledwindow29.show()
        self.scrolledwindow29.set_shadow_type(gtk.SHADOW_NONE)

        self.DownloadList = gtk.TreeView()
        self.DownloadList.show()
        self.DownloadList.set_headers_visible(True)
        self.scrolledwindow29.add(self.DownloadList)

        self.vboxdownloads.pack_start(self.scrolledwindow29, True, True, 0)

        self.hbox18 = gtk.HBox(False, 5)
        self.hbox18.show()
        self.hbox18.set_spacing(5)

        self.clearFinishedAbortedButton = gtk.Button()
        self.clearFinishedAbortedButton.show()

        self.alignment21 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment21.show()

        self.hbox41 = gtk.HBox(False, 2)
        self.hbox41.show()
        self.hbox41.set_spacing(2)

        self.image21 = gtk.Image()
        self.image21.set_padding(0, 0)
        self.image21.set_from_stock(gtk.STOCK_CLEAR, 4)
        self.image21.show()
        self.hbox41.pack_start(self.image21, False, False, 0)

        self.label50 = gtk.Label(_("Clear Finished / Aborted"))
        self.label50.set_padding(0, 0)
        self.label50.show()
        self.hbox41.pack_start(self.label50, False, False, 0)

        self.alignment21.add(self.hbox41)

        self.clearFinishedAbortedButton.add(self.alignment21)

        self.hbox18.pack_start(self.clearFinishedAbortedButton, False, False, 0)

        self.clearQueuedButton = gtk.Button()
        self.clearQueuedButton.show()

        self.alignment22 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment22.show()

        self.hbox42 = gtk.HBox(False, 2)
        self.hbox42.show()
        self.hbox42.set_spacing(2)

        self.image22 = gtk.Image()
        self.image22.set_padding(0, 0)
        self.image22.set_from_stock(gtk.STOCK_CLEAR, 4)
        self.image22.show()
        self.hbox42.pack_start(self.image22, False, False, 0)

        self.label51 = gtk.Label(_("Clear Queued"))
        self.label51.set_padding(0, 0)
        self.label51.show()
        self.hbox42.pack_start(self.label51, False, False, 0)

        self.alignment22.add(self.hbox42)

        self.clearQueuedButton.add(self.alignment22)

        self.hbox18.pack_start(self.clearQueuedButton, False, False, 0)

        self.retryTransferButton = gtk.Button()
        self.retryTransferButton.show()

        self.alignment15 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment15.show()

        self.hbox35 = gtk.HBox(False, 2)
        self.hbox35.show()
        self.hbox35.set_spacing(2)

        self.image15 = gtk.Image()
        self.image15.set_padding(0, 0)
        self.image15.set_from_stock(gtk.STOCK_REDO, 4)
        self.image15.show()
        self.hbox35.pack_start(self.image15, False, False, 0)

        self.label44 = gtk.Label(_("Retry"))
        self.label44.set_padding(0, 0)
        self.label44.show()
        self.hbox35.pack_start(self.label44, False, False, 0)

        self.alignment15.add(self.hbox35)

        self.retryTransferButton.add(self.alignment15)

        self.hbox18.pack_start(self.retryTransferButton, False, False, 1)

        self.abortTransferButton = gtk.Button()
        self.abortTransferButton.show()

        self.alignment16 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment16.show()

        self.hbox36 = gtk.HBox(False, 2)
        self.hbox36.show()
        self.hbox36.set_spacing(2)

        self.image16 = gtk.Image()
        self.image16.set_padding(0, 0)
        self.image16.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image16.show()
        self.hbox36.pack_start(self.image16, False, False, 0)

        self.label45 = gtk.Label(_("Abort"))
        self.label45.set_padding(0, 0)
        self.label45.show()
        self.hbox36.pack_start(self.label45, False, False, 0)

        self.alignment16.add(self.hbox36)

        self.abortTransferButton.add(self.alignment16)

        self.hbox18.pack_start(self.abortTransferButton, False, False, 0)

        self.deleteTransferButton = gtk.Button()
        self.deleteTransferButton.show()

        self.alignment9 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment9.show()

        self.hbox29 = gtk.HBox(False, 2)
        self.hbox29.show()
        self.hbox29.set_spacing(2)

        self.image9 = gtk.Image()
        self.image9.set_padding(0, 0)
        self.image9.set_from_stock(gtk.STOCK_DELETE, 4)
        self.image9.show()
        self.hbox29.pack_start(self.image9, False, False, 0)

        self.label38 = gtk.Label(_("Abort & Delete"))
        self.label38.set_padding(0, 0)
        self.label38.show()
        self.hbox29.pack_start(self.label38, False, False, 0)

        self.alignment9.add(self.hbox29)

        self.deleteTransferButton.add(self.alignment9)

        self.hbox18.pack_start(self.deleteTransferButton, False, False, 0)

        self.banDownloadButton = gtk.Button()
        self.banDownloadButton.show()

        self.alignment13 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment13.show()

        self.hbox33 = gtk.HBox(False, 2)
        self.hbox33.show()
        self.hbox33.set_spacing(2)

        self.image13 = gtk.Image()
        self.image13.set_padding(0, 0)
        self.image13.set_from_stock(gtk.STOCK_STOP, 4)
        self.image13.show()
        self.hbox33.pack_start(self.image13, False, False, 0)

        self.label42 = gtk.Label(_("Ban User(s)"))
        self.label42.set_padding(0, 0)
        self.label42.show()
        self.hbox33.pack_start(self.label42, False, False, 0)

        self.alignment13.add(self.hbox33)

        self.banDownloadButton.add(self.alignment13)

        self.hbox18.pack_end(self.banDownloadButton, False, False, 0)

        self.vboxdownloads.pack_start(self.hbox18, False, True, 0)

        self.custom3 = self.get_custom_widget("custom3", _("ImageLabel"), _("Downloads"), 0, 0)
        self.custom3.show()
        self.vboxuploads = gtk.VBox(False, 0)
        self.vboxuploads.show()
        self.vboxuploads.set_spacing(0)

        self.scrolledwindow30 = gtk.ScrolledWindow()
        self.scrolledwindow30.set_policy(gtk.POLICY_ALWAYS, gtk.POLICY_ALWAYS)
        self.scrolledwindow30.show()
        self.scrolledwindow30.set_shadow_type(gtk.SHADOW_NONE)

        self.UploadList = gtk.TreeView()
        self.UploadList.show()
        self.UploadList.set_headers_visible(True)
        self.scrolledwindow30.add(self.UploadList)

        self.vboxuploads.pack_start(self.scrolledwindow30, True, True, 0)

        self.hbox19 = gtk.HBox(False, 5)
        self.hbox19.show()
        self.hbox19.set_spacing(5)

        self.clearUploadFinishedAbortedButton = gtk.Button()
        self.clearUploadFinishedAbortedButton.show()

        self.alignment20 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment20.show()

        self.hbox40 = gtk.HBox(False, 2)
        self.hbox40.show()
        self.hbox40.set_spacing(2)

        self.image20 = gtk.Image()
        self.image20.set_padding(0, 0)
        self.image20.set_from_stock(gtk.STOCK_CLEAR, 4)
        self.image20.show()
        self.hbox40.pack_start(self.image20, False, False, 0)

        self.label49 = gtk.Label(_("Clear Finished / Aborted"))
        self.label49.set_padding(0, 0)
        self.label49.show()
        self.hbox40.pack_start(self.label49, False, False, 0)

        self.alignment20.add(self.hbox40)

        self.clearUploadFinishedAbortedButton.add(self.alignment20)

        self.hbox19.pack_start(self.clearUploadFinishedAbortedButton, False, False, 0)

        self.clearUploadQueueButton = gtk.Button()
        self.clearUploadQueueButton.show()

        self.alignment19 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment19.show()

        self.hbox39 = gtk.HBox(False, 2)
        self.hbox39.show()
        self.hbox39.set_spacing(2)

        self.image19 = gtk.Image()
        self.image19.set_padding(0, 0)
        self.image19.set_from_stock(gtk.STOCK_CLEAR, 4)
        self.image19.show()
        self.hbox39.pack_start(self.image19, False, False, 0)

        self.label48 = gtk.Label(_("Clear Queued"))
        self.label48.set_padding(0, 0)
        self.label48.show()
        self.hbox39.pack_start(self.label48, False, False, 0)

        self.alignment19.add(self.hbox39)

        self.clearUploadQueueButton.add(self.alignment19)

        self.hbox19.pack_start(self.clearUploadQueueButton, False, False, 0)

        self.abortUploadButton = gtk.Button()
        self.abortUploadButton.show()

        self.alignment17 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment17.show()

        self.hbox37 = gtk.HBox(False, 2)
        self.hbox37.show()
        self.hbox37.set_spacing(2)

        self.image17 = gtk.Image()
        self.image17.set_padding(0, 0)
        self.image17.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image17.show()
        self.hbox37.pack_start(self.image17, False, False, 0)

        self.label46 = gtk.Label(_("Abort"))
        self.label46.set_padding(0, 0)
        self.label46.show()
        self.hbox37.pack_start(self.label46, False, False, 0)

        self.alignment17.add(self.hbox37)

        self.abortUploadButton.add(self.alignment17)

        self.hbox19.pack_start(self.abortUploadButton, False, False, 0)

        self.banUploadButton = gtk.Button()
        self.banUploadButton.show()

        self.alignment14 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment14.show()

        self.hbox34 = gtk.HBox(False, 2)
        self.hbox34.show()
        self.hbox34.set_spacing(2)

        self.image14 = gtk.Image()
        self.image14.set_padding(0, 0)
        self.image14.set_from_stock(gtk.STOCK_STOP, 4)
        self.image14.show()
        self.hbox34.pack_start(self.image14, False, False, 0)

        self.label43 = gtk.Label(_("Ban User(s)"))
        self.label43.set_padding(0, 0)
        self.label43.show()
        self.hbox34.pack_start(self.label43, False, False, 0)

        self.alignment14.add(self.hbox34)

        self.banUploadButton.add(self.alignment14)

        self.hbox19.pack_end(self.banUploadButton, False, False, 0)

        self.abortUserUploadButton = gtk.Button()
        self.abortUserUploadButton.show()

        self.alignment18 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment18.show()

        self.hbox38 = gtk.HBox(False, 2)
        self.hbox38.show()
        self.hbox38.set_spacing(2)

        self.image18 = gtk.Image()
        self.image18.set_padding(0, 0)
        self.image18.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image18.show()
        self.hbox38.pack_start(self.image18, False, False, 0)

        self.label47 = gtk.Label(_("Abort User's Uploads(s)"))
        self.label47.set_padding(0, 0)
        self.label47.show()
        self.hbox38.pack_start(self.label47, False, False, 0)

        self.alignment18.add(self.hbox38)

        self.abortUserUploadButton.add(self.alignment18)

        self.hbox19.pack_start(self.abortUserUploadButton, False, False, 0)

        self.vboxuploads.pack_start(self.hbox19, False, True, 0)

        self.custom10 = self.get_custom_widget("custom10", _("ImageLabel"), _("Uploads"), 0, 0)
        self.custom10.show()
        self.searchvbox = gtk.VBox(False, 0)
        self.searchvbox.show()
        self.searchvbox.set_spacing(0)

        self.hbox2 = gtk.HBox(False, 0)
        self.hbox2.show()
        self.hbox2.set_spacing(0)

        self.combo1_List = gtk.ListStore(gobject.TYPE_STRING)
        self.combo1 = gtk.ComboBoxEntry()
        self.combo1.show()

        self.SearchEntry = self.combo1.child
        self.SearchEntry.set_text("")
        self.SearchEntry.set_editable(True)
        self.SearchEntry.show()
        self.SearchEntry.set_visibility(True)
        self.SearchEntry.connect("activate", self.OnSearch)

        self.combo1.set_model(self.combo1_List)
        self.combo1.set_text_column(0)
        self.hbox2.pack_start(self.combo1, True, True, 0)

        self.GlobalRadio = gtk.RadioButton()
        self.GlobalRadio.set_active(False)
        self.GlobalRadio.set_label(_("Global"))
        self.GlobalRadio.show()

        self.hbox2.pack_start(self.GlobalRadio, False, False, 0)

        self.RoomsRadio = gtk.RadioButton(self.GlobalRadio)
        self.RoomsRadio.set_active(False)
        self.RoomsRadio.set_label(_("Rooms"))
        self.RoomsRadio.show()

        self.hbox2.pack_start(self.RoomsRadio, False, False, 0)

        self.BuddiesRadio = gtk.RadioButton(self.GlobalRadio)
        self.BuddiesRadio.set_active(False)
        self.BuddiesRadio.set_label(_("Buddies"))
        self.BuddiesRadio.show()

        self.hbox2.pack_start(self.BuddiesRadio, False, False, 0)

        self.SearchButton = gtk.Button()
        self.SearchButton.show()
        self.SearchButton.connect("clicked", self.OnSearch)

        self.alignment3 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment3.show()

        self.hbox23 = gtk.HBox(False, 2)
        self.hbox23.show()
        self.hbox23.set_spacing(2)

        self.image3 = gtk.Image()
        self.image3.set_padding(0, 0)
        self.image3.set_from_stock(gtk.STOCK_FIND, 4)
        self.image3.show()
        self.hbox23.pack_start(self.image3, False, False, 0)

        self.label32 = gtk.Label(_("Search"))
        self.label32.set_padding(0, 0)
        self.label32.show()
        self.hbox23.pack_start(self.label32, False, False, 0)

        self.alignment3.add(self.hbox23)

        self.SearchButton.add(self.alignment3)

        self.hbox2.pack_start(self.SearchButton, False, False, 0)

        self.searchvbox.pack_start(self.hbox2, False, True, 0)

        self.SearchNotebook = self.get_custom_widget("SearchNotebook", "", "", 0, 0)
        self.SearchNotebook.show()
        self.searchvbox.pack_start(self.SearchNotebook, True, True, 0)

        self.SearchTabLabel = self.get_custom_widget("SearchTabLabel", _("ImageLabel"), _("Search files"), 0, 0)
        self.SearchTabLabel.show()
        self.userinfovbox = gtk.VBox(False, 0)
        self.userinfovbox.show()
        self.userinfovbox.set_spacing(0)

        self.UserInfoNotebook = self.get_custom_widget("UserInfoNotebook", "", "", 0, 0)
        self.UserInfoNotebook.show()
        self.userinfovbox.pack_start(self.UserInfoNotebook, True, True, 0)

        self.hbox21 = gtk.HBox(False, 5)
        self.hbox21.show()
        self.hbox21.set_spacing(5)
        self.hbox21.set_border_width(5)

        self.sUserinfoButton = gtk.Button()
        self.sUserinfoButton.show()

        self.alignment12 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment12.show()

        self.hbox32 = gtk.HBox(False, 2)
        self.hbox32.show()
        self.hbox32.set_spacing(2)

        self.image12 = gtk.Image()
        self.image12.set_padding(0, 0)
        self.image12.set_from_stock(gtk.STOCK_JUMP_TO, 4)
        self.image12.show()
        self.hbox32.pack_start(self.image12, False, False, 0)

        self.label41 = gtk.Label(_("Get Userinfo"))
        self.label41.set_padding(0, 0)
        self.label41.show()
        self.hbox32.pack_start(self.label41, False, False, 0)

        self.alignment12.add(self.hbox32)

        self.sUserinfoButton.add(self.alignment12)

        self.hbox21.pack_end(self.sUserinfoButton, False, False, 0)

        self.UserinfoEntry = gtk.Entry()
        self.UserinfoEntry.set_text("")
        self.UserinfoEntry.set_editable(True)
        self.UserinfoEntry.show()
        self.UserinfoEntry.set_visibility(True)
        self.hbox21.pack_end(self.UserinfoEntry, False, True, 0)

        self.label30 = gtk.Label(_("Input a user:"))
        self.label30.set_padding(0, 0)
        self.label30.show()
        self.hbox21.pack_end(self.label30, False, False, 0)

        self.userinfovbox.pack_start(self.hbox21, False, True, 0)

        self.UserInfoTabLabel = self.get_custom_widget("UserInfoTabLabel", _("ImageLabel"), _("User info"), 0, 0)
        self.UserInfoTabLabel.show()
        self.userbrowsevbox = gtk.VBox(False, 0)
        self.userbrowsevbox.show()
        self.userbrowsevbox.set_spacing(0)

        self.UserBrowseNotebook = self.get_custom_widget("UserBrowseNotebook", "", "", 0, 0)
        self.UserBrowseNotebook.show()
        self.userbrowsevbox.pack_start(self.UserBrowseNotebook, True, True, 0)

        self.hbox22 = gtk.HBox(False, 5)
        self.hbox22.show()
        self.hbox22.set_spacing(5)
        self.hbox22.set_border_width(5)

        self.sSharesButton = gtk.Button()
        self.sSharesButton.show()

        self.alignment11 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment11.show()

        self.hbox31 = gtk.HBox(False, 2)
        self.hbox31.show()
        self.hbox31.set_spacing(2)

        self.image11 = gtk.Image()
        self.image11.set_padding(0, 0)
        self.image11.set_from_stock(gtk.STOCK_JUMP_TO, 4)
        self.image11.show()
        self.hbox31.pack_start(self.image11, False, False, 0)

        self.label40 = gtk.Label(_("Get Shares"))
        self.label40.set_padding(0, 0)
        self.label40.show()
        self.hbox31.pack_start(self.label40, False, False, 0)

        self.alignment11.add(self.hbox31)

        self.sSharesButton.add(self.alignment11)

        self.hbox22.pack_end(self.sSharesButton, False, False, 0)

        self.SharesEntry = gtk.Entry()
        self.SharesEntry.set_text("")
        self.SharesEntry.set_editable(True)
        self.SharesEntry.show()
        self.SharesEntry.set_visibility(True)
        self.hbox22.pack_end(self.SharesEntry, False, True, 0)

        self.label31 = gtk.Label(_("Input a user:"))
        self.label31.set_padding(0, 0)
        self.label31.show()
        self.hbox22.pack_end(self.label31, False, False, 0)

        self.userbrowsevbox.pack_start(self.hbox22, False, True, 0)

        self.UserBrowseTabLabel = self.get_custom_widget("UserBrowseTabLabel", _("ImageLabel"), _("User browse"), 0, 0)
        self.UserBrowseTabLabel.show()
        self.interests = gtk.VBox(False, 10)
        self.interests.show()
        self.interests.set_spacing(10)
        self.interests.set_border_width(10)

        self.hbox12 = gtk.HBox(False, 5)
        self.hbox12.show()
        self.hbox12.set_spacing(5)

        self.button19 = gtk.Button()
        self.button19.show()
        self.button19.connect("clicked", self.OnSimilarUsersClicked)

        self.alignment6 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment6.show()

        self.hbox26 = gtk.HBox(False, 2)
        self.hbox26.show()
        self.hbox26.set_spacing(2)

        self.image6 = gtk.Image()
        self.image6.set_padding(0, 0)
        self.image6.set_from_stock(gtk.STOCK_REFRESH, 4)
        self.image6.show()
        self.hbox26.pack_start(self.image6, False, False, 0)

        self.label35 = gtk.Label(_("Similar users"))
        self.label35.set_padding(0, 0)
        self.label35.show()
        self.hbox26.pack_start(self.label35, False, False, 0)

        self.alignment6.add(self.hbox26)

        self.button19.add(self.alignment6)

        self.hbox12.pack_end(self.button19, False, False, 0)

        self.button18 = gtk.Button()
        self.button18.show()
        self.button18.connect("clicked", self.OnRecommendationsClicked)

        self.alignment5 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment5.show()

        self.hbox25 = gtk.HBox(False, 2)
        self.hbox25.show()
        self.hbox25.set_spacing(2)

        self.image5 = gtk.Image()
        self.image5.set_padding(0, 0)
        self.image5.set_from_stock(gtk.STOCK_REFRESH, 4)
        self.image5.show()
        self.hbox25.pack_start(self.image5, False, False, 0)

        self.label34 = gtk.Label(_("Recommendations"))
        self.label34.set_padding(0, 0)
        self.label34.show()
        self.hbox25.pack_start(self.label34, False, False, 0)

        self.alignment5.add(self.hbox25)

        self.button18.add(self.alignment5)

        self.hbox12.pack_end(self.button18, False, False, 0)

        self.button17 = gtk.Button()
        self.button17.show()
        self.button17.connect("clicked", self.OnGlobalRecommendationsClicked)

        self.alignment4 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment4.show()

        self.hbox24 = gtk.HBox(False, 2)
        self.hbox24.show()
        self.hbox24.set_spacing(2)

        self.image4 = gtk.Image()
        self.image4.set_padding(0, 0)
        self.image4.set_from_stock(gtk.STOCK_REFRESH, 4)
        self.image4.show()
        self.hbox24.pack_start(self.image4, False, False, 0)

        self.label33 = gtk.Label(_("Global recommendations"))
        self.label33.set_padding(0, 0)
        self.label33.show()
        self.hbox24.pack_start(self.label33, False, False, 0)

        self.alignment4.add(self.hbox24)

        self.button17.add(self.alignment4)

        self.hbox12.pack_end(self.button17, False, False, 0)

        self.interests.pack_start(self.hbox12, False, True, 0)

        self.hbox11 = gtk.HBox(False, 5)
        self.hbox11.show()
        self.hbox11.set_spacing(5)

        self.hpaned3 = gtk.HPaned()
        self.hpaned3.show()

        self.vbox13 = gtk.VBox(True, 10)
        self.vbox13.set_size_request(200, -1)
        self.vbox13.show()
        self.vbox13.set_spacing(10)

        self.vbox14 = gtk.VBox(False, 5)
        self.vbox14.show()
        self.vbox14.set_spacing(5)

        self.scrolledwindow23 = gtk.ScrolledWindow()
        self.scrolledwindow23.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolledwindow23.show()
        self.scrolledwindow23.set_shadow_type(gtk.SHADOW_IN)

        self.LikesList = gtk.TreeView()
        self.LikesList.show()
        self.LikesList.set_headers_visible(True)
        self.scrolledwindow23.add(self.LikesList)

        self.vbox14.pack_start(self.scrolledwindow23, True, True, 0)

        self.button15 = gtk.Button()
        self.button15.show()
        self.button15.connect("clicked", self.OnAddThingILike)

        self.alignment2 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment2.show()

        self.hbox15 = gtk.HBox(False, 2)
        self.hbox15.show()
        self.hbox15.set_spacing(2)

        self.image2 = gtk.Image()
        self.image2.set_padding(0, 0)
        self.image2.set_from_stock(gtk.STOCK_ADD, 4)
        self.image2.show()
        self.hbox15.pack_start(self.image2, False, False, 0)

        self.label22 = gtk.Label(_("Add"))
        self.label22.set_padding(0, 0)
        self.label22.show()
        self.hbox15.pack_start(self.label22, False, False, 0)

        self.alignment2.add(self.hbox15)

        self.button15.add(self.alignment2)

        self.vbox14.pack_start(self.button15, False, False, 0)

        self.vbox13.pack_start(self.vbox14, True, True, 0)

        self.vbox15 = gtk.VBox(False, 5)
        self.vbox15.show()
        self.vbox15.set_spacing(5)

        self.scrolledwindow24 = gtk.ScrolledWindow()
        self.scrolledwindow24.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolledwindow24.show()
        self.scrolledwindow24.set_shadow_type(gtk.SHADOW_IN)

        self.DislikesList = gtk.TreeView()
        self.DislikesList.show()
        self.DislikesList.set_headers_visible(True)
        self.scrolledwindow24.add(self.DislikesList)

        self.vbox15.pack_start(self.scrolledwindow24, True, True, 0)

        self.button16 = gtk.Button()
        self.button16.show()
        self.button16.connect("clicked", self.OnAddThingIDislike)

        self.alignment1 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment1.show()

        self.hbox14 = gtk.HBox(False, 2)
        self.hbox14.show()
        self.hbox14.set_spacing(2)

        self.image1 = gtk.Image()
        self.image1.set_padding(0, 0)
        self.image1.set_from_stock(gtk.STOCK_ADD, 4)
        self.image1.show()
        self.hbox14.pack_start(self.image1, False, False, 0)

        self.label21 = gtk.Label(_("Add"))
        self.label21.set_padding(0, 0)
        self.label21.show()
        self.hbox14.pack_start(self.label21, False, False, 0)

        self.alignment1.add(self.hbox14)

        self.button16.add(self.alignment1)

        self.vbox15.pack_start(self.button16, False, False, 0)

        self.vbox13.pack_start(self.vbox15, True, True, 0)

        self.hpaned3.pack1(self.vbox13, False, True)

        self.hpaned4 = gtk.HPaned()
        self.hpaned4.show()

        self.scrolledwindow26 = gtk.ScrolledWindow()
        self.scrolledwindow26.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolledwindow26.show()
        self.scrolledwindow26.set_shadow_type(gtk.SHADOW_IN)

        self.RecommendationsList = gtk.TreeView()
        self.RecommendationsList.show()
        self.RecommendationsList.set_headers_visible(True)
        self.scrolledwindow26.add(self.RecommendationsList)

        self.hpaned4.pack1(self.scrolledwindow26, True, True)

        self.scrolledwindow27 = gtk.ScrolledWindow()
        self.scrolledwindow27.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolledwindow27.show()
        self.scrolledwindow27.set_shadow_type(gtk.SHADOW_IN)

        self.RecommendationUsersList = gtk.TreeView()
        self.RecommendationUsersList.show()
        self.RecommendationUsersList.set_headers_visible(True)
        self.scrolledwindow27.add(self.RecommendationUsersList)

        self.hpaned4.pack2(self.scrolledwindow27, True, True)

        self.hpaned3.pack2(self.hpaned4, True, True)

        self.hbox11.pack_start(self.hpaned3, True, True, 0)

        self.interests.pack_start(self.hbox11, True, True, 0)

        self.InterestsTabLabel = self.get_custom_widget("InterestsTabLabel", _("ImageLabel"), _("Interests"), 0, 0)
        self.InterestsTabLabel.show()
        self.notebook1.append_page(self.hpaned1, self.ChatTabLabel)

        self.notebook1.append_page(self.privatevbox, self.PrivateChatTabLabel)

        self.notebook1.append_page(self.vboxdownloads, self.custom3)

        self.notebook1.append_page(self.vboxuploads, self.custom10)

        self.notebook1.append_page(self.searchvbox, self.SearchTabLabel)

        self.notebook1.append_page(self.userinfovbox, self.UserInfoTabLabel)

        self.notebook1.append_page(self.userbrowsevbox, self.UserBrowseTabLabel)

        self.notebook1.append_page(self.interests, self.InterestsTabLabel)

        self.vpaned1.pack1(self.notebook1, True, True)

        self.vbox1.pack_start(self.vpaned1, True, True, 0)

        self.hbox10 = gtk.HBox(False, 0)
        self.hbox10.show()
        self.hbox10.set_spacing(0)
        self.hbox10.set_border_width(2)

        self.Statusbar = gtk.Statusbar()
        self.Statusbar.set_has_resize_grip(False)
        self.Statusbar.show()
        self.Statusbar.set_border_width(1)
        self.hbox10.pack_start(self.Statusbar, True, True, 0)

        self.UserStatus = gtk.Statusbar()
        self.UserStatus.set_size_request(100, -1)
        self.UserStatus.set_has_resize_grip(False)
        self.UserStatus.show()
        self.UserStatus.set_border_width(1)
        self.hbox10.pack_start(self.UserStatus, False, True, 0)

        self.DownStatus = gtk.Statusbar()
        self.DownStatus.set_size_request(150, -1)
        self.DownStatus.set_has_resize_grip(False)
        self.DownStatus.show()
        self.DownStatus.set_border_width(1)
        self.hbox10.pack_start(self.DownStatus, False, True, 0)

        self.UpStatus = gtk.Statusbar()
        self.UpStatus.set_size_request(150, -1)
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

    def OnShowDebug(self, widget):
        pass

    def OnHideLog(self, widget):
        pass

    def OnHideRoomList(self, widget):
        pass

    def OnHideTickers(self, widget):
        pass

    def OnToggleBuddyList(self, widget):
        pass

    def OnSettings(self, widget):
        pass

    def OnRescan(self, widget):
        pass

    def OnBuddyRescan(self, widget):
        pass

    def OnBrowseMyShares(self, widget):
        pass

    def OnExit(self, widget):
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

    def OnAboutChatroomCommands(self, widget):
        pass

    def OnAboutPrivateChatCommands(self, widget):
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
    def __init__(self, create = True, accel_group = None):
        if accel_group is None:
             self.accel_group = gtk.AccelGroup()
        else:
             self.accel_group = accel_group
        if create:
            self.ChatRoomTab = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.ChatRoomTab.set_title(_("window1"))
            self.ChatRoomTab.set_position(gtk.WIN_POS_NONE)
            self.ChatRoomTab.add_accel_group(self.accel_group)
            self.ChatRoomTab.show()

        self.Main = gtk.HPaned()
        self.Main.show()

        self.vpaned2 = gtk.VPaned()
        self.vpaned2.show()

        self.scrolledwindow13 = gtk.ScrolledWindow()
        self.scrolledwindow13.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolledwindow13.show()
        self.scrolledwindow13.set_shadow_type(gtk.SHADOW_IN)

        self.RoomLog = gtk.TextView()
        self.RoomLog.set_wrap_mode(gtk.WRAP_NONE)
        self.RoomLog.set_cursor_visible(False)
        self.RoomLog.set_editable(False)
        self.RoomLog.show()
        self.scrolledwindow13.add(self.RoomLog)

        self.vpaned2.pack1(self.scrolledwindow13, False, True)

        self.vbox6 = gtk.VBox(False, 0)
        self.vbox6.show()
        self.vbox6.set_spacing(0)

        self.Ticker = self.get_custom_widget("Ticker", "", "", 0, 0)
        self.Ticker.connect("button_press_event", self.OnTickerClicked)
        self.vbox6.pack_start(self.Ticker, False, True, 0)

        self.scrolledwindow15 = gtk.ScrolledWindow()
        self.scrolledwindow15.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolledwindow15.show()
        self.scrolledwindow15.set_shadow_type(gtk.SHADOW_IN)

        self.ChatScroll = gtk.TextView()
        self.ChatScroll.set_wrap_mode(gtk.WRAP_WORD)
        self.ChatScroll.set_cursor_visible(False)
        self.ChatScroll.set_editable(False)
        self.ChatScroll.show()
        self.scrolledwindow15.add(self.ChatScroll)

        self.vbox6.pack_start(self.scrolledwindow15, True, True, 0)

        self.entry3 = gtk.Entry()
        self.entry3.set_text("")
        self.entry3.set_editable(True)
        self.entry3.show()
        self.entry3.set_visibility(True)
        self.entry3.connect("activate", self.OnEnter)
        self.entry3.connect("key_press_event", self.OnKeyPress)
        self.vbox6.pack_start(self.entry3, False, False, 0)

        self.vpaned2.pack2(self.vbox6, True, True)

        self.Main.pack1(self.vpaned2, True, True)

        self.vbox5 = gtk.VBox(False, 0)
        self.vbox5.show()
        self.vbox5.set_spacing(0)

        self.scrolledwindow14 = gtk.ScrolledWindow()
        self.scrolledwindow14.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolledwindow14.show()
        self.scrolledwindow14.set_shadow_type(gtk.SHADOW_IN)

        self.UserList = gtk.TreeView()
        self.UserList.show()
        self.UserList.set_headers_visible(True)
        self.scrolledwindow14.add(self.UserList)

        self.vbox5.pack_start(self.scrolledwindow14, True, True, 0)

        self.Encoding_List = gtk.ListStore(gobject.TYPE_STRING)
        self.Encoding = gtk.ComboBox()
        self.Encoding.show()
        self.Encoding.connect("changed", self.OnEncodingChanged)

        self.Encoding.set_model(self.Encoding_List)
        cell = gtk.CellRendererText()
        self.Encoding.pack_start(cell, True)
        self.Encoding.add_attribute(cell, 'text', 0)
        self.vbox5.pack_start(self.Encoding, False, False, 0)

        self.hbox4 = gtk.HBox(False, 0)
        self.hbox4.show()
        self.hbox4.set_spacing(0)

        self.Log = gtk.CheckButton()
        self.Log.set_active(False)
        self.Log.set_label(_("Log"))
        self.Log.show()
        self.Log.connect("toggled", self.OnLogToggled)
        self.hbox4.pack_start(self.Log, False, False, 0)

        self.AutoJoin = gtk.CheckButton()
        self.AutoJoin.set_active(False)
        self.AutoJoin.set_label(_("Auto-join"))
        self.AutoJoin.show()
        self.AutoJoin.connect("toggled", self.OnAutojoin)
        self.hbox4.pack_start(self.AutoJoin, False, False, 0)

        self.Leave = gtk.Button()
        self.Leave.set_label(_("Leave"))
        self.Leave.show()
        self.Leave.connect("clicked", self.OnLeave)

        self.hbox4.pack_end(self.Leave, False, False, 0)

        self.vbox5.pack_start(self.hbox4, False, True, 0)

        self.Main.pack2(self.vbox5, False, True)


        if create:
            self.ChatRoomTab.add(self.Main)

    def OnTickerClicked(self, widget):
        pass

    def OnEnter(self, widget):
        pass

    def OnKeyPress(self, widget):
        pass

    def OnEncodingChanged(self, widget):
        pass

    def OnLogToggled(self, widget):
        pass

    def OnAutojoin(self, widget):
        pass

    def OnLeave(self, widget):
        pass

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class PrivateChatTab:
    def __init__(self, create = True, accel_group = None):
        if accel_group is None:
             self.accel_group = gtk.AccelGroup()
        else:
             self.accel_group = accel_group
        if create:
            self.PrivateChatTab = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.PrivateChatTab.set_title(_("window1"))
            self.PrivateChatTab.set_position(gtk.WIN_POS_NONE)
            self.PrivateChatTab.add_accel_group(self.accel_group)
            self.PrivateChatTab.show()

        self.Main = gtk.VBox(False, 0)
        self.Main.show()
        self.Main.set_spacing(0)

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

        self.Main.pack_start(self.scrolledwindow16, True, True, 0)

        self.hbox5 = gtk.HBox(False, 0)
        self.hbox5.show()
        self.hbox5.set_spacing(0)

        self.ChatLine = gtk.Entry()
        self.ChatLine.set_text("")
        self.ChatLine.set_editable(True)
        self.ChatLine.show()
        self.ChatLine.set_visibility(True)
        self.ChatLine.connect("activate", self.OnEnter)
        self.ChatLine.connect("key_press_event", self.OnKeyPress)
        self.hbox5.pack_start(self.ChatLine, True, True, 0)

        self.Encoding_List = gtk.ListStore(gobject.TYPE_STRING)
        self.Encoding = gtk.ComboBox()
        self.Encoding.show()
        self.Encoding.connect("changed", self.OnEncodingChanged)

        self.Encoding.set_model(self.Encoding_List)
        cell = gtk.CellRendererText()
        self.Encoding.pack_start(cell, True)
        self.Encoding.add_attribute(cell, 'text', 0)
        self.hbox5.pack_start(self.Encoding, False, False, 0)

        self.Log = gtk.CheckButton()
        self.Log.set_active(False)
        self.Log.set_label(_("Log"))
        self.Log.show()
        self.Log.connect("toggled", self.OnLogToggled)
        self.hbox5.pack_start(self.Log, False, False, 0)

        self.button1 = gtk.Button()
        self.button1.set_label(_("Close"))
        self.button1.show()
        self.button1.connect("clicked", self.OnClose)

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
    def __init__(self, create = True, accel_group = None):
        if accel_group is None:
             self.accel_group = gtk.AccelGroup()
        else:
             self.accel_group = accel_group
        if create:
            self.SearchTab = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.SearchTab.set_title(_("window1"))
            self.SearchTab.set_position(gtk.WIN_POS_NONE)
            self.SearchTab.add_accel_group(self.accel_group)
            self.SearchTab.show()

        self.vbox7 = gtk.VBox(False, 0)
        self.vbox7.show()
        self.vbox7.set_spacing(0)

        self.hbox6 = gtk.HBox(False, 5)
        self.hbox6.show()
        self.hbox6.set_spacing(5)

        self.checkbutton1 = gtk.CheckButton()
        self.checkbutton1.set_active(False)
        self.checkbutton1.set_label(_("Enable filters"))
        self.checkbutton1.show()
        self.checkbutton1.connect("toggled", self.OnToggleFilters)
        self.hbox6.pack_start(self.checkbutton1, True, True, 0)

        self.button2 = gtk.Button()
        self.button2.set_label(_("Ignore"))
        self.button2.show()
        self.button2.connect("clicked", self.OnIgnore)

        self.hbox6.pack_start(self.button2, False, False, 0)

        self.button3 = gtk.Button()
        self.button3.set_label(_("Close"))
        self.button3.show()
        self.button3.connect("clicked", self.OnClose)

        self.hbox6.pack_start(self.button3, False, False, 0)

        self.RememberCheckButton = gtk.CheckButton()
        self.RememberCheckButton.set_active(False)
        self.RememberCheckButton.set_label(_("Remember"))
        self.RememberCheckButton.show()
        self.RememberCheckButton.connect("toggled", self.OnToggleRemember)
        self.hbox6.pack_start(self.RememberCheckButton, False, False, 0)

        self.vbox7.pack_start(self.hbox6, False, True, 0)

        self.Filters = gtk.HBox(False, 2)
        self.Filters.set_spacing(2)

        self.label13 = gtk.Label(_("Filter in:"))
        self.label13.set_padding(0, 0)
        self.label13.show()
        self.Filters.pack_start(self.label13, False, False, 0)

        self.FilterIn_List = gtk.ListStore(gobject.TYPE_STRING)
        self.FilterIn = gtk.ComboBoxEntry()
        self.FilterIn.show()

        self.combo_entry1 = self.FilterIn.child
        self.combo_entry1.set_text("")
        self.combo_entry1.set_editable(True)
        self.combo_entry1.show()
        self.combo_entry1.set_visibility(True)
        self.combo_entry1.connect("activate", self.OnRefilter)

        self.FilterIn.set_model(self.FilterIn_List)
        self.FilterIn.set_text_column(0)
        self.Filters.pack_start(self.FilterIn, True, True, 0)

        self.label14 = gtk.Label(_("Filter out:"))
        self.label14.set_padding(0, 0)
        self.label14.show()
        self.Filters.pack_start(self.label14, False, False, 0)

        self.FilterOut_List = gtk.ListStore(gobject.TYPE_STRING)
        self.FilterOut = gtk.ComboBoxEntry()
        self.FilterOut.show()

        self.combo_entry2 = self.FilterOut.child
        self.combo_entry2.set_text("")
        self.combo_entry2.set_editable(True)
        self.combo_entry2.show()
        self.combo_entry2.set_visibility(True)
        self.combo_entry2.connect("activate", self.OnRefilter)

        self.FilterOut.set_model(self.FilterOut_List)
        self.FilterOut.set_text_column(0)
        self.Filters.pack_start(self.FilterOut, True, True, 0)

        self.label15 = gtk.Label(_("Size:"))
        self.label15.set_padding(0, 0)
        self.label15.show()
        self.Filters.pack_start(self.label15, False, False, 0)

        self.FilterSize_List = gtk.ListStore(gobject.TYPE_STRING)
        self.FilterSize = gtk.ComboBoxEntry()
        self.FilterSize.set_size_request(75, -1)
        self.FilterSize.show()

        self.combo_entry3 = self.FilterSize.child
        self.combo_entry3.set_text("")
        self.combo_entry3.set_editable(True)
        self.combo_entry3.show()
        self.combo_entry3.set_visibility(True)
        self.combo_entry3.connect("activate", self.OnRefilter)

        self.FilterSize.set_model(self.FilterSize_List)
        self.FilterSize.set_text_column(0)
        self.Filters.pack_start(self.FilterSize, False, True, 0)

        self.label16 = gtk.Label(_("Bitrate:"))
        self.label16.set_padding(0, 0)
        self.label16.show()
        self.Filters.pack_start(self.label16, False, False, 0)

        self.FilterBitrate_List = gtk.ListStore(gobject.TYPE_STRING)
        self.FilterBitrate = gtk.ComboBoxEntry()
        self.FilterBitrate.set_size_request(75, -1)
        self.FilterBitrate.show()

        self.combo_entry4 = self.FilterBitrate.child
        self.combo_entry4.set_text("")
        self.combo_entry4.set_editable(True)
        self.combo_entry4.show()
        self.combo_entry4.set_visibility(True)
        self.combo_entry4.connect("activate", self.OnRefilter)

        self.FilterBitrate.set_model(self.FilterBitrate_List)
        self.FilterBitrate.set_text_column(0)
        self.Filters.pack_start(self.FilterBitrate, False, True, 0)

        self.label23 = gtk.Label(_("Country:"))
        self.label23.set_padding(0, 0)
        self.label23.show()
        self.Filters.pack_start(self.label23, False, False, 0)

        self.FilterCountry_List = gtk.ListStore(gobject.TYPE_STRING)
        self.FilterCountry = gtk.ComboBoxEntry()
        self.FilterCountry.set_size_request(75, -1)
        self.FilterCountry.show()

        self.combo_entry5 = self.FilterCountry.child
        self.combo_entry5.set_text("")
        self.combo_entry5.set_editable(True)
        self.combo_entry5.show()
        self.combo_entry5.set_visibility(True)
        self.combo_entry5.connect("activate", self.OnRefilter)

        self.FilterCountry.set_model(self.FilterCountry_List)
        self.FilterCountry.set_text_column(0)
        self.Filters.pack_start(self.FilterCountry, False, True, 0)

        self.FilterFreeSlot = gtk.CheckButton()
        self.FilterFreeSlot.set_active(False)
        self.FilterFreeSlot.set_label(_("Free slot"))
        self.FilterFreeSlot.show()
        self.FilterFreeSlot.connect("toggled", self.OnRefilter)
        self.Filters.pack_start(self.FilterFreeSlot, False, False, 0)

        self.vbox7.pack_start(self.Filters, False, True, 0)

        self.scrolledwindow17 = gtk.ScrolledWindow()
        self.scrolledwindow17.set_policy(gtk.POLICY_ALWAYS, gtk.POLICY_ALWAYS)
        self.scrolledwindow17.show()
        self.scrolledwindow17.set_shadow_type(gtk.SHADOW_IN)

        self.ResultsList = gtk.TreeView()
        self.ResultsList.show()
        self.ResultsList.set_headers_visible(True)
        self.scrolledwindow17.add(self.ResultsList)

        self.vbox7.pack_start(self.scrolledwindow17, True, True, 0)


        if create:
            self.SearchTab.add(self.vbox7)

    def OnToggleFilters(self, widget):
        pass

    def OnIgnore(self, widget):
        pass

    def OnClose(self, widget):
        pass

    def OnToggleRemember(self, widget):
        pass

    def OnRefilter(self, widget):
        pass

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class UserInfoTab:
    def __init__(self, create = True, accel_group = None):
        if accel_group is None:
             self.accel_group = gtk.AccelGroup()
        else:
             self.accel_group = accel_group
        if create:
            self.UserInfoTab = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.UserInfoTab.set_title(_("window1"))
            self.UserInfoTab.set_position(gtk.WIN_POS_NONE)
            self.UserInfoTab.add_accel_group(self.accel_group)
            self.UserInfoTab.show()

        self.Main = gtk.HBox(False, 0)
        self.Main.show()
        self.Main.set_spacing(0)

        self.hpaned5 = gtk.HPaned()
        self.hpaned5.show()

        self.vbox8 = gtk.VBox(False, 0)
        self.vbox8.set_size_request(250, -1)
        self.vbox8.show()
        self.vbox8.set_spacing(0)

        self.frame1 = gtk.Frame()
        self.frame1.show()
        self.frame1.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        self.vbox16 = gtk.VBox(False, 0)
        self.vbox16.show()
        self.vbox16.set_spacing(0)

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

        self.vbox16.pack_start(self.scrolledwindow28, True, True, 0)

        self.frame1.add(self.vbox16)

        self.label17 = gtk.Label(_("Self description:"))
        self.label17.set_padding(0, 0)
        self.label17.show()
        self.frame1.set_label_widget(self.label17)

        self.vbox8.pack_start(self.frame1, True, True, 0)

        self.frame2 = gtk.Frame()
        self.frame2.show()
        self.frame2.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        self.vbox10 = gtk.VBox(False, 10)
        self.vbox10.show()
        self.vbox10.set_spacing(10)
        self.vbox10.set_border_width(10)

        self.uploads = gtk.Label(_("Total uploads allowed: unknown"))
        self.uploads.set_alignment(0, 0.5)
        self.uploads.set_padding(0, 0)
        self.uploads.show()
        self.vbox10.pack_start(self.uploads, False, False, 0)

        self.queuesize = gtk.Label(_("Queue size: unknown"))
        self.queuesize.set_alignment(0, 0.5)
        self.queuesize.set_padding(0, 0)
        self.queuesize.show()
        self.vbox10.pack_start(self.queuesize, False, False, 0)

        self.hbox17 = gtk.HBox(False, 5)
        self.hbox17.show()
        self.hbox17.set_spacing(5)

        self.slotsavail = gtk.Label(_("Slots available: unknown"))
        self.slotsavail.set_alignment(0, 0.5)
        self.slotsavail.set_padding(0, 0)
        self.slotsavail.show()
        self.hbox17.pack_start(self.slotsavail, False, False, 0)

        self.speed = gtk.Label(_("Speed: unknown"))
        self.speed.set_alignment(0, 0.5)
        self.speed.set_padding(0, 0)
        self.speed.show()
        self.hbox17.pack_start(self.speed, False, False, 0)

        self.vbox10.pack_start(self.hbox17, False, False, 0)

        self.hbox16 = gtk.HBox(False, 5)
        self.hbox16.show()
        self.hbox16.set_spacing(5)

        self.filesshared = gtk.Label(_("Files Shared: unknown"))
        self.filesshared.set_alignment(0, 0.5)
        self.filesshared.set_padding(0, 0)
        self.filesshared.show()
        self.hbox16.pack_start(self.filesshared, False, False, 0)

        self.dirsshared = gtk.Label(_("Dirs Shared: unknown"))
        self.dirsshared.set_alignment(0, 0.5)
        self.dirsshared.set_padding(0, 0)
        self.dirsshared.show()
        self.hbox16.pack_start(self.dirsshared, False, False, 0)

        self.vbox10.pack_start(self.hbox16, False, False, 0)

        self.progressbar = gtk.ProgressBar()
        self.progressbar.show()
        self.vbox10.pack_end(self.progressbar, False, True, 0)

        self.frame2.add(self.vbox10)

        self.label18 = gtk.Label(_("Information:"))
        self.label18.set_padding(0, 0)
        self.label18.show()
        self.frame2.set_label_widget(self.label18)

        self.vbox8.pack_start(self.frame2, False, True, 0)

        self.hpaned5.pack1(self.vbox8, False, True)

        self.frame3 = gtk.Frame()
        self.frame3.show()
        self.frame3.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        self.scrolledwindow19 = gtk.ScrolledWindow()
        self.scrolledwindow19.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolledwindow19.show()
        self.scrolledwindow19.set_shadow_type(gtk.SHADOW_NONE)

        self.viewport2 = gtk.Viewport()
        self.viewport2.show()
        self.viewport2.set_shadow_type(gtk.SHADOW_NONE)

        self.image = gtk.Image()
        self.image.set_padding(0, 0)
        self.image.show()
        self.viewport2.add(self.image)

        self.scrolledwindow19.add(self.viewport2)

        self.frame3.add(self.scrolledwindow19)

        self.label19 = gtk.Label(_("Picture:"))
        self.label19.set_padding(0, 0)
        self.label19.show()
        self.frame3.set_label_widget(self.label19)

        self.hpaned5.pack2(self.frame3, True, True)

        self.Main.pack_start(self.hpaned5, True, True, 0)

        self.vbox9 = gtk.VBox(False, 10)
        self.vbox9.show()
        self.vbox9.set_spacing(10)
        self.vbox9.set_border_width(10)

        self.button4 = gtk.Button()
        self.button4.set_label(_("Private chat"))
        self.button4.show()
        self.button4.connect("clicked", self.OnSendMessage)

        self.vbox9.pack_start(self.button4, False, False, 0)

        self.button5 = gtk.Button()
        self.button5.set_label(_("Browse"))
        self.button5.show()
        self.button5.connect("clicked", self.OnBrowseUser)

        self.vbox9.pack_start(self.button5, False, False, 0)

        self.button6 = gtk.Button()
        self.button6.set_label(_("Show IP"))
        self.button6.show()
        self.button6.connect("clicked", self.OnShowIPaddress)

        self.vbox9.pack_start(self.button6, False, False, 0)

        self.button7 = gtk.Button()
        self.button7.set_label(_("Add to list"))
        self.button7.show()
        self.button7.connect("clicked", self.OnAddToList)

        self.vbox9.pack_start(self.button7, False, False, 0)

        self.button8 = gtk.Button()
        self.button8.set_label(_("Ban"))
        self.button8.show()
        self.button8.connect("clicked", self.OnBanUser)

        self.vbox9.pack_start(self.button8, False, False, 0)

        self.button14 = gtk.Button()
        self.button14.set_label(_("Ignore"))
        self.button14.show()
        self.button14.connect("clicked", self.OnIgnoreUser)

        self.vbox9.pack_start(self.button14, False, False, 0)

        self.button9 = gtk.Button()
        self.button9.set_label(_("Save pic"))
        self.button9.show()
        self.button9.connect("clicked", self.OnSavePicture)

        self.vbox9.pack_start(self.button9, False, False, 0)

        self.button10 = gtk.Button()
        self.button10.set_label(_("Close"))
        self.button10.show()
        self.button10.connect("clicked", self.OnClose)

        self.vbox9.pack_end(self.button10, False, False, 0)

        self.button11 = gtk.Button()
        self.button11.set_label(_("Refresh"))
        self.button11.show()
        self.button11.connect("clicked", self.OnRefresh)

        self.vbox9.pack_end(self.button11, False, False, 0)

        self.Main.pack_start(self.vbox9, False, True, 0)


        if create:
            self.UserInfoTab.add(self.Main)

    def OnEncodingChanged(self, widget):
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

    def OnClose(self, widget):
        pass

    def OnRefresh(self, widget):
        pass

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class UserBrowseTab:
    def __init__(self, create = True, accel_group = None):
        if accel_group is None:
             self.accel_group = gtk.AccelGroup()
        else:
             self.accel_group = accel_group
        if create:
            self.UserBrowseTab = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.UserBrowseTab.set_title(_("window1"))
            self.UserBrowseTab.set_position(gtk.WIN_POS_NONE)
            self.UserBrowseTab.add_accel_group(self.accel_group)
            self.UserBrowseTab.show()

        self.Main = gtk.VBox(False, 0)
        self.Main.show()
        self.Main.set_spacing(0)

        self.hbox8 = gtk.HBox(False, 5)
        self.hbox8.show()
        self.hbox8.set_spacing(5)

        self.label20 = gtk.Label(_("Search file and folder names (exact match):"))
        self.label20.set_padding(0, 0)
        self.label20.show()
        self.hbox8.pack_start(self.label20, False, False, 0)

        self.entry4 = gtk.Entry()
        self.entry4.set_text("")
        self.entry4.set_editable(True)
        self.entry4.show()
        self.entry4.set_visibility(True)
        self.entry4.connect("activate", self.OnSearch)
        self.hbox8.pack_start(self.entry4, True, True, 0)

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

        self.scrolledwindow21 = gtk.ScrolledWindow()
        self.scrolledwindow21.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolledwindow21.set_size_request(250, -1)
        self.scrolledwindow21.show()
        self.scrolledwindow21.set_shadow_type(gtk.SHADOW_IN)

        self.FolderTreeView = gtk.TreeView()
        self.FolderTreeView.show()
        self.FolderTreeView.set_headers_visible(False)
        self.scrolledwindow21.add(self.FolderTreeView)

        self.hpaned2.pack1(self.scrolledwindow21, False, True)

        self.sMain = gtk.VBox(False, 0)
        self.sMain.show()
        self.sMain.set_spacing(0)

        self.hbox9 = gtk.HBox(False, 5)
        self.hbox9.show()
        self.hbox9.set_spacing(5)
        self.hbox9.set_border_width(10)

        self.progressbar1 = gtk.ProgressBar()
        self.progressbar1.set_size_request(250, -1)
        self.progressbar1.show()
        self.hbox9.pack_start(self.progressbar1, False, False, 0)

        self.button12 = gtk.Button(None, gtk.STOCK_CLOSE)
        self.button12.show()
        self.button12.connect("clicked", self.OnClose)

        self.hbox9.pack_end(self.button12, False, False, 0)

        self.button13 = gtk.Button(None, gtk.STOCK_REFRESH)
        self.button13.show()
        self.button13.connect("clicked", self.OnRefresh)

        self.hbox9.pack_end(self.button13, False, False, 0)

        self.sMain.pack_start(self.hbox9, False, True, 0)

        self.scrolledwindow20 = gtk.ScrolledWindow()
        self.scrolledwindow20.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolledwindow20.show()
        self.scrolledwindow20.set_shadow_type(gtk.SHADOW_IN)

        self.FileTreeView = gtk.TreeView()
        self.FileTreeView.show()
        self.FileTreeView.set_headers_visible(True)
        self.scrolledwindow20.add(self.FileTreeView)

        self.sMain.pack_start(self.scrolledwindow20, True, True, 0)

        self.hpaned2.pack2(self.sMain, True, True)

        self.Main.pack_start(self.hpaned2, True, True, 0)


        if create:
            self.UserBrowseTab.add(self.Main)

    def OnSearch(self, widget):
        pass

    def OnEncodingChanged(self, widget):
        pass

    def OnClose(self, widget):
        pass

    def OnRefresh(self, widget):
        pass

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class RoomList:
    def __init__(self, create = True, accel_group = None):
        if accel_group is None:
             self.accel_group = gtk.AccelGroup()
        else:
             self.accel_group = accel_group
        if create:
            self.RoomList = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.RoomList.set_title(_("window1"))
            self.RoomList.set_position(gtk.WIN_POS_NONE)
            self.RoomList.add_accel_group(self.accel_group)
            self.RoomList.show()

        self.vbox2 = gtk.VBox(False, 0)
        self.vbox2.show()
        self.vbox2.set_spacing(0)

        self.scrolledwindow10 = gtk.ScrolledWindow()
        self.scrolledwindow10.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolledwindow10.show()
        self.scrolledwindow10.set_shadow_type(gtk.SHADOW_IN)

        self.RoomsList = gtk.TreeView()
        self.RoomsList.show()
        self.RoomsList.set_headers_visible(True)
        self.scrolledwindow10.add(self.RoomsList)

        self.vbox2.pack_start(self.scrolledwindow10, True, True, 0)

        self.hbox1 = gtk.HBox(False, 0)
        self.hbox1.show()
        self.hbox1.set_spacing(0)

        self.label10 = gtk.Label(_("Create: "))
        self.label10.set_padding(0, 0)
        self.label10.show()
        self.hbox1.pack_start(self.label10, False, False, 0)

        self.CreateRoomEntry = gtk.Entry()
        self.CreateRoomEntry.set_text("")
        self.CreateRoomEntry.set_editable(True)
        self.CreateRoomEntry.show()
        self.CreateRoomEntry.set_visibility(True)
        self.CreateRoomEntry.connect("activate", self.OnCreateRoom)
        self.hbox1.pack_start(self.CreateRoomEntry, True, True, 0)

        self.vbox2.pack_start(self.hbox1, False, True, 0)


        if create:
            self.RoomList.add(self.vbox2)

    def OnCreateRoom(self, widget):
        pass

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

