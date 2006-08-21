import gtk, gobject
from pynicotine.utils import _

class ServerFrame:
    def __init__(self, create = True, accel_group = None):
        if accel_group is None:
             self.accel_group = gtk.AccelGroup()
        else:
             self.accel_group = accel_group
        if create:
            self.ServerFrame = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.ServerFrame.set_title(_("Server Settings"))
            self.ServerFrame.set_position(gtk.WIN_POS_NONE)
            self.ServerFrame.add_accel_group(self.accel_group)
            self.ServerFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()
        self.Main.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        self.vbox71 = gtk.VBox(False, 10)
        self.vbox71.show()
        self.vbox71.set_spacing(10)
        self.vbox71.set_border_width(5)

        self.vbox72 = gtk.VBox(False, 0)
        self.vbox72.show()
        self.vbox72.set_spacing(0)

        self.label166 = gtk.Label(_("Server: (use server.slsknet.org:2240 for the main server)"))
        self.label166.set_alignment(0, 0)
        self.label166.set_size_request(360, -1)
        self.label166.set_padding(0, 0)
        self.label166.set_line_wrap(True)
        self.label166.show()
        self.vbox72.pack_start(self.label166, False, False, 3)

        self.hbox103 = gtk.HBox(False, 0)
        self.hbox103.show()
        self.hbox103.set_spacing(0)

        self.Server_List = gtk.ListStore(gobject.TYPE_STRING)
        self.Server = gtk.ComboBoxEntry()
        self.Server.set_size_request(200, -1)
        self.Server.show()

        self.entry66 = self.Server.child
        self.entry66.set_size_request(103, -1)
        self.entry66.set_text("")
        self.entry66.set_editable(True)
        self.entry66.show()
        self.entry66.set_visibility(True)

        self.Server.set_model(self.Server_List)
        self.Server.set_text_column(0)
        self.hbox103.pack_start(self.Server, False, False, 0)

        self.vbox72.pack_start(self.hbox103, False, False, 0)

        self.vbox71.pack_start(self.vbox72, False, True, 0)

        self.hbox104 = gtk.HBox(False, 10)
        self.hbox104.show()
        self.hbox104.set_spacing(10)

        self.vbox73 = gtk.VBox(False, 0)
        self.vbox73.show()
        self.vbox73.set_spacing(0)

        self.label167 = gtk.Label(_("Login:"))
        self.label167.set_alignment(0, 0.5)
        self.label167.set_size_request(57, -1)
        self.label167.set_padding(0, 0)
        self.label167.set_line_wrap(False)
        self.label167.show()
        self.vbox73.pack_start(self.label167, False, False, 0)

        self.Login = gtk.Entry()
        self.Login.set_size_request(130, -1)
        self.Login.set_text("")
        self.Login.set_editable(True)
        self.Login.show()
        self.Login.set_visibility(True)
        self.vbox73.pack_start(self.Login, False, False, 0)

        self.hbox104.pack_start(self.vbox73, False, False, 0)

        self.vseparator8 = gtk.VSeparator()
        self.vseparator8.show()
        self.hbox104.pack_start(self.vseparator8, False, False, 0)

        self.vbox74 = gtk.VBox(False, 0)
        self.vbox74.show()
        self.vbox74.set_spacing(0)

        self.label168 = gtk.Label(_("Password:"))
        self.label168.set_alignment(0, 0)
        self.label168.set_size_request(5, -1)
        self.label168.set_padding(0, 0)
        self.label168.set_line_wrap(False)
        self.label168.show()
        self.vbox74.pack_start(self.label168, False, False, 0)

        self.Password = gtk.Entry()
        self.Password.set_size_request(100, -1)
        self.Password.set_text("")
        self.Password.set_editable(True)
        self.Password.show()
        self.Password.set_visibility(False)
        self.vbox74.pack_start(self.Password, False, False, 0)

        self.hbox104.pack_start(self.vbox74, False, False, 0)

        self.vbox71.pack_start(self.hbox104, False, True, 0)

        self.vbox75 = gtk.VBox(False, 0)
        self.vbox75.show()
        self.vbox75.set_spacing(0)

        self.label169 = gtk.Label(_("Network Character Encoding (utf-8 is a good choice)"))
        self.label169.set_alignment(0.0500000007451, 0.5)
        self.label169.set_padding(0, 0)
        self.label169.set_line_wrap(False)
        self.label169.show()
        self.vbox75.pack_start(self.label169, False, False, 0)

        self.hbox108 = gtk.HBox(False, 0)
        self.hbox108.show()
        self.hbox108.set_spacing(0)

        self.Encoding_List = gtk.ListStore(gobject.TYPE_STRING)
        self.Encoding = gtk.ComboBoxEntry()
        self.Encoding.set_size_request(100, -1)
        self.Encoding.show()

        self.combo_entry2 = self.Encoding.child
        self.combo_entry2.set_text("")
        self.combo_entry2.set_editable(False)
        self.combo_entry2.show()
        self.combo_entry2.set_visibility(True)

        self.Encoding.set_model(self.Encoding_List)
        self.Encoding.set_text_column(0)
        self.hbox108.pack_start(self.Encoding, False, False, 0)

        self.vbox75.pack_start(self.hbox108, False, False, 0)

        self.vbox71.pack_start(self.vbox75, False, True, 0)

        self.vbox76 = gtk.VBox(False, 0)
        self.vbox76.show()
        self.vbox76.set_spacing(0)

        self.label172 = gtk.Label(_("Client connection ports (use first available):"))
        self.label172.set_alignment(0, 0.5)
        self.label172.set_padding(0, 0)
        self.label172.set_line_wrap(False)
        self.label172.show()
        self.vbox76.pack_start(self.label172, False, False, 0)

        self.hbox106 = gtk.HBox(False, 5)
        self.hbox106.set_size_request(114, -1)
        self.hbox106.show()
        self.hbox106.set_spacing(5)

        self.FirstPort = gtk.Entry()
        self.FirstPort.set_size_request(50, -1)
        self.FirstPort.set_text("2234")
        self.FirstPort.set_editable(True)
        self.FirstPort.show()
        self.FirstPort.set_visibility(True)
        self.hbox106.pack_start(self.FirstPort, False, False, 0)

        self.label173 = gtk.Label(_("-"))
        self.label173.set_size_request(0, -1)
        self.label173.set_padding(0, 0)
        self.label173.set_line_wrap(False)
        self.label173.show()
        self.hbox106.pack_start(self.label173, False, False, 0)

        self.LastPort = gtk.Entry()
        self.LastPort.set_size_request(50, -1)
        self.LastPort.set_text("2242")
        self.LastPort.set_editable(True)
        self.LastPort.show()
        self.LastPort.set_visibility(True)
        self.hbox106.pack_start(self.LastPort, False, False, 0)

        self.vbox76.pack_start(self.hbox106, True, True, 3)

        self.label260 = gtk.Label(_("Use the above ports to configure your router or firewall."))
        self.label260.set_alignment(0, 0.5)
        self.label260.set_padding(0, 11)
        self.label260.set_line_wrap(False)
        self.label260.show()
        self.vbox76.pack_start(self.label260, False, False, 0)

        self.DirectConnection = gtk.CheckButton()
        self.DirectConnection.set_active(False)
        self.DirectConnection.set_label(_("I can receive direct connections"))
        self.DirectConnection.show()
        self.vbox76.pack_start(self.DirectConnection, False, False, 0)

        self.label271 = gtk.Label(_("(only use if the above ports are remotely accessable)"))
        self.label271.set_alignment(0, 0.5)
        self.label271.set_padding(0, 0)
        self.label271.set_line_wrap(False)
        self.label271.show()
        self.vbox76.pack_start(self.label271, False, False, 0)

        self.vbox71.pack_start(self.vbox76, False, False, 0)

        self.ctcptogglebutton = gtk.CheckButton()
        self.ctcptogglebutton.set_active(False)
        self.ctcptogglebutton.set_label(_("Enable CTCP-like PM responses (Client Version)"))
        self.ctcptogglebutton.show()
        self.vbox71.pack_start(self.ctcptogglebutton, False, False, 0)

        self.Main.add(self.vbox71)

        self.label165 = gtk.Label(_("Server"))
        self.label165.set_padding(0, 0)
        self.label165.set_line_wrap(False)
        self.label165.show()
        self.Main.set_label_widget(self.label165)


        if create:
            self.ServerFrame.add(self.Main)

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class SharesFrame:
    def __init__(self, create = True, accel_group = None):
        if accel_group is None:
             self.accel_group = gtk.AccelGroup()
        else:
             self.accel_group = accel_group
        if create:
            self.SharesFrame = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.SharesFrame.set_title(_("Shares"))
            self.SharesFrame.set_position(gtk.WIN_POS_NONE)
            self.SharesFrame.add_accel_group(self.accel_group)
            self.SharesFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()
        self.Main.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        self.vbox77 = gtk.VBox(False, 7)
        self.vbox77.show()
        self.vbox77.set_spacing(7)
        self.vbox77.set_border_width(5)

        self.vbox78 = gtk.VBox(False, 0)
        self.vbox78.show()
        self.vbox78.set_spacing(0)

        self.label176 = gtk.Label(_("Incomplete file directory:"))
        self.label176.set_alignment(0, 0.5)
        self.label176.set_padding(0, 0)
        self.label176.set_line_wrap(False)
        self.label176.show()
        self.vbox78.pack_start(self.label176, False, False, 0)

        self.hbox109 = gtk.HBox(False, 5)
        self.hbox109.show()
        self.hbox109.set_spacing(5)

        self.IncompleteDir = gtk.Entry()
        self.IncompleteDir.set_size_request(250, -1)
        self.IncompleteDir.set_text("")
        self.IncompleteDir.set_editable(True)
        self.IncompleteDir.show()
        self.IncompleteDir.set_visibility(True)
        self.hbox109.pack_start(self.IncompleteDir, False, False, 0)

        self.button73 = gtk.Button()
        self.button73.show()
        self.button73.connect("clicked", self.OnChooseIncompleteDir)

        self.alignment58 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment58.show()

        self.hbox152 = gtk.HBox(False, 2)
        self.hbox152.show()
        self.hbox152.set_spacing(2)

        self.image55 = gtk.Image()
        self.image55.set_padding(0, 0)
        self.image55.set_from_stock(gtk.STOCK_OPEN, 4)
        self.image55.show()
        self.hbox152.pack_start(self.image55, False, False, 0)

        self.label231 = gtk.Label(_("Choose..."))
        self.label231.set_padding(0, 0)
        self.label231.set_line_wrap(False)
        self.label231.show()
        self.hbox152.pack_start(self.label231, False, False, 0)

        self.alignment58.add(self.hbox152)

        self.button73.add(self.alignment58)

        self.hbox109.pack_start(self.button73, False, False, 0)

        self.vbox78.pack_start(self.hbox109, False, False, 0)

        self.vbox77.pack_start(self.vbox78, False, False, 0)

        self.vbox79 = gtk.VBox(False, 0)
        self.vbox79.show()
        self.vbox79.set_spacing(0)

        self.label178 = gtk.Label(_("Download directory:"))
        self.label178.set_alignment(0, 0.5)
        self.label178.set_padding(0, 0)
        self.label178.set_line_wrap(False)
        self.label178.show()
        self.vbox79.pack_start(self.label178, False, False, 0)

        self.hbox111 = gtk.HBox(False, 5)
        self.hbox111.show()
        self.hbox111.set_spacing(5)

        self.DownloadDir = gtk.Entry()
        self.DownloadDir.set_size_request(250, -1)
        self.DownloadDir.set_text("")
        self.DownloadDir.set_editable(True)
        self.DownloadDir.show()
        self.DownloadDir.set_visibility(True)
        self.hbox111.pack_start(self.DownloadDir, False, False, 0)

        self.button74 = gtk.Button()
        self.button74.show()
        self.button74.connect("clicked", self.OnChooseDownloadDir)

        self.alignment59 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment59.show()

        self.hbox153 = gtk.HBox(False, 2)
        self.hbox153.show()
        self.hbox153.set_spacing(2)

        self.image56 = gtk.Image()
        self.image56.set_padding(0, 0)
        self.image56.set_from_stock(gtk.STOCK_OPEN, 4)
        self.image56.show()
        self.hbox153.pack_start(self.image56, False, False, 0)

        self.label232 = gtk.Label(_("Choose..."))
        self.label232.set_padding(0, 0)
        self.label232.set_line_wrap(False)
        self.label232.show()
        self.hbox153.pack_start(self.label232, False, False, 0)

        self.alignment59.add(self.hbox153)

        self.button74.add(self.alignment59)

        self.hbox111.pack_start(self.button74, False, False, 0)

        self.vbox79.pack_start(self.hbox111, False, False, 0)

        self.ShareDownloadDir = gtk.CheckButton()
        self.ShareDownloadDir.set_active(False)
        self.ShareDownloadDir.set_label(_("Share download directory"))
        self.ShareDownloadDir.show()
        self.ShareDownloadDir.connect("toggled", self.OnShareDownloadDirToggled)
        self.vbox79.pack_start(self.ShareDownloadDir, False, False, 0)

        self.vbox77.pack_start(self.vbox79, False, False, 0)

        self.RescanOnStartup = gtk.CheckButton()
        self.RescanOnStartup.set_active(False)
        self.RescanOnStartup.set_label(_("Rescan shares on startup"))
        self.RescanOnStartup.show()
        self.vbox77.pack_start(self.RescanOnStartup, False, False, 0)

        self.hbox113 = gtk.HBox(False, 5)
        self.hbox113.show()
        self.hbox113.set_spacing(5)

        self.scrolledwindow8 = gtk.ScrolledWindow()
        self.scrolledwindow8.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolledwindow8.set_size_request(250, -1)
        self.scrolledwindow8.show()
        self.scrolledwindow8.set_shadow_type(gtk.SHADOW_IN)

        self.Shares = gtk.TreeView()
        self.Shares.show()
        self.Shares.set_headers_visible(False)
        self.scrolledwindow8.add(self.Shares)

        self.hbox113.pack_start(self.scrolledwindow8, False, False, 0)

        self.vbox80 = gtk.VBox(False, 0)
        self.vbox80.show()
        self.vbox80.set_spacing(0)

        self.addSharesButton = gtk.Button()
        self.addSharesButton.show()
        self.addSharesButton.connect("clicked", self.OnAddSharedDir)

        self.alignment60 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment60.show()

        self.hbox154 = gtk.HBox(False, 2)
        self.hbox154.show()
        self.hbox154.set_spacing(2)

        self.image57 = gtk.Image()
        self.image57.set_padding(0, 0)
        self.image57.set_from_stock(gtk.STOCK_OPEN, 4)
        self.image57.show()
        self.hbox154.pack_start(self.image57, False, False, 0)

        self.label233 = gtk.Label(_("Add..."))
        self.label233.set_padding(0, 0)
        self.label233.set_line_wrap(False)
        self.label233.show()
        self.hbox154.pack_start(self.label233, False, False, 0)

        self.alignment60.add(self.hbox154)

        self.addSharesButton.add(self.alignment60)

        self.vbox80.pack_start(self.addSharesButton, False, False, 0)

        self.removeSharesButton = gtk.Button()
        self.removeSharesButton.show()
        self.removeSharesButton.connect("clicked", self.OnRemoveSharedDir)

        self.alignment61 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment61.show()

        self.hbox155 = gtk.HBox(False, 2)
        self.hbox155.show()
        self.hbox155.set_spacing(2)

        self.image58 = gtk.Image()
        self.image58.set_padding(0, 0)
        self.image58.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image58.show()
        self.hbox155.pack_start(self.image58, False, False, 0)

        self.label234 = gtk.Label(_("Remove"))
        self.label234.set_padding(0, 0)
        self.label234.set_line_wrap(False)
        self.label234.show()
        self.hbox155.pack_start(self.label234, False, False, 0)

        self.alignment61.add(self.hbox155)

        self.removeSharesButton.add(self.alignment61)

        self.vbox80.pack_start(self.removeSharesButton, False, False, 0)

        self.hbox113.pack_start(self.vbox80, False, False, 0)

        self.vbox77.pack_start(self.hbox113, True, True, 0)

        self.enableBuddyShares = gtk.CheckButton()
        self.enableBuddyShares.set_active(False)
        self.enableBuddyShares.set_label(_("Enable Buddy-Only shares"))
        self.enableBuddyShares.show()
        self.enableBuddyShares.connect("toggled", self.OnEnabledBuddySharesToggled)
        self.vbox77.pack_start(self.enableBuddyShares, False, False, 0)

        self.hbox166 = gtk.HBox(False, 5)
        self.hbox166.show()
        self.hbox166.set_spacing(5)

        self.scrolledwindow15 = gtk.ScrolledWindow()
        self.scrolledwindow15.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolledwindow15.set_size_request(250, -1)
        self.scrolledwindow15.show()
        self.scrolledwindow15.set_shadow_type(gtk.SHADOW_IN)

        self.BuddyShares = gtk.TreeView()
        self.BuddyShares.show()
        self.BuddyShares.set_headers_visible(False)
        self.scrolledwindow15.add(self.BuddyShares)

        self.hbox166.pack_start(self.scrolledwindow15, False, False, 0)

        self.vbox103 = gtk.VBox(False, 0)
        self.vbox103.show()
        self.vbox103.set_spacing(0)

        self.addBuddySharesButton = gtk.Button()
        self.addBuddySharesButton.show()
        self.addBuddySharesButton.connect("clicked", self.OnAddSharedBuddyDir)

        self.alignment71 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment71.show()

        self.hbox167 = gtk.HBox(False, 2)
        self.hbox167.show()
        self.hbox167.set_spacing(2)

        self.image65 = gtk.Image()
        self.image65.set_padding(0, 0)
        self.image65.set_from_stock(gtk.STOCK_OPEN, 4)
        self.image65.show()
        self.hbox167.pack_start(self.image65, False, False, 0)

        self.label290 = gtk.Label(_("Add..."))
        self.label290.set_padding(0, 0)
        self.label290.set_line_wrap(False)
        self.label290.show()
        self.hbox167.pack_start(self.label290, False, False, 0)

        self.alignment71.add(self.hbox167)

        self.addBuddySharesButton.add(self.alignment71)

        self.vbox103.pack_start(self.addBuddySharesButton, False, False, 0)

        self.removeBuddySharesButton = gtk.Button()
        self.removeBuddySharesButton.show()
        self.removeBuddySharesButton.connect("clicked", self.OnRemoveSharedBuddyDir)

        self.alignment72 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment72.show()

        self.hbox168 = gtk.HBox(False, 2)
        self.hbox168.show()
        self.hbox168.set_spacing(2)

        self.image66 = gtk.Image()
        self.image66.set_padding(0, 0)
        self.image66.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image66.show()
        self.hbox168.pack_start(self.image66, False, False, 0)

        self.label293 = gtk.Label(_("Remove"))
        self.label293.set_padding(0, 0)
        self.label293.set_line_wrap(False)
        self.label293.show()
        self.hbox168.pack_start(self.label293, False, False, 0)

        self.alignment72.add(self.hbox168)

        self.removeBuddySharesButton.add(self.alignment72)

        self.vbox103.pack_start(self.removeBuddySharesButton, False, False, 0)

        self.hbox166.pack_start(self.vbox103, False, False, 0)

        self.vbox77.pack_start(self.hbox166, True, True, 0)

        self.Main.add(self.vbox77)

        self.label175 = gtk.Label(_("Shares"))
        self.label175.set_padding(0, 0)
        self.label175.set_line_wrap(False)
        self.label175.show()
        self.Main.set_label_widget(self.label175)


        if create:
            self.SharesFrame.add(self.Main)

    def OnChooseIncompleteDir(self, widget):
        pass

    def OnChooseDownloadDir(self, widget):
        pass

    def OnShareDownloadDirToggled(self, widget):
        pass

    def OnAddSharedDir(self, widget):
        pass

    def OnRemoveSharedDir(self, widget):
        pass

    def OnEnabledBuddySharesToggled(self, widget):
        pass

    def OnAddSharedBuddyDir(self, widget):
        pass

    def OnRemoveSharedBuddyDir(self, widget):
        pass

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class TransfersFrame:
    def __init__(self, create = True, accel_group = None):
        if accel_group is None:
             self.accel_group = gtk.AccelGroup()
        else:
             self.accel_group = accel_group
        if create:
            self.TransfersFrame = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.TransfersFrame.set_title(_("Transfers"))
            self.TransfersFrame.set_position(gtk.WIN_POS_NONE)
            self.TransfersFrame.add_accel_group(self.accel_group)
            self.TransfersFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()
        self.Main.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        self.vbox81 = gtk.VBox(False, 5)
        self.vbox81.show()
        self.vbox81.set_spacing(5)
        self.vbox81.set_border_width(5)

        self.vbox82 = gtk.VBox(False, 0)
        self.vbox82.show()
        self.vbox82.set_spacing(0)

        self.hbox117 = gtk.HBox(False, 5)
        self.hbox117.show()
        self.hbox117.set_spacing(5)

        self.label185 = gtk.Label(_("If Uploads are sent at"))
        self.label185.set_padding(0, 0)
        self.label185.set_line_wrap(False)
        self.label185.show()
        self.hbox117.pack_start(self.label185, False, False, 0)

        self.QueueBandwidth = gtk.Entry()
        self.QueueBandwidth.set_size_request(30, -1)
        self.QueueBandwidth.set_text("")
        self.QueueBandwidth.set_editable(True)
        self.QueueBandwidth.show()
        self.QueueBandwidth.set_visibility(True)
        self.hbox117.pack_start(self.QueueBandwidth, False, False, 0)

        self.label186 = gtk.Label(_("KBytes/sec then other uploads will be queued."))
        self.label186.set_padding(0, 0)
        self.label186.set_line_wrap(True)
        self.label186.show()
        self.hbox117.pack_start(self.label186, False, False, 0)

        self.vbox82.pack_start(self.hbox117, False, False, 0)

        self.hbox118 = gtk.HBox(False, 5)
        self.hbox118.show()
        self.hbox118.set_spacing(5)

        self.QueueUseSlots = gtk.CheckButton()
        self.QueueUseSlots.set_active(False)
        self.QueueUseSlots.set_label(_("Limit number of uploads to"))
        self.QueueUseSlots.show()
        self.QueueUseSlots.connect("toggled", self.OnQueueUseSlotsToggled)
        self.hbox118.pack_start(self.QueueUseSlots, False, False, 0)

        self.QueueSlots = gtk.Entry()
        self.QueueSlots.set_size_request(30, -1)
        self.QueueSlots.set_text("")
        self.QueueSlots.set_editable(True)
        self.QueueSlots.show()
        self.QueueSlots.set_visibility(True)
        self.hbox118.pack_start(self.QueueSlots, False, False, 0)

        self.label254 = gtk.Label(_("(NOT RECOMMENDED)"))
        self.label254.set_padding(0, 0)
        self.label254.set_line_wrap(False)
        self.label254.show()
        self.hbox118.pack_start(self.label254, False, False, 0)

        self.vbox82.pack_start(self.hbox118, False, False, 0)

        self.vbox81.pack_start(self.vbox82, False, False, 0)

        self.table1 = gtk.Table()
        self.table1.show()
        self.table1.set_row_spacings(0)
        self.table1.set_col_spacings(5)

        self.LimitSpeed = gtk.Entry()
        self.LimitSpeed.set_size_request(30, -1)
        self.LimitSpeed.set_text("")
        self.LimitSpeed.set_editable(True)
        self.LimitSpeed.show()
        self.LimitSpeed.set_visibility(True)
        self.table1.attach(self.LimitSpeed, 1, 2, 0, 1, 0, 0, 0, 0)

        self.label188 = gtk.Label(_("KBytes/sec"))
        self.label188.set_padding(0, 0)
        self.label188.set_line_wrap(False)
        self.label188.show()
        self.table1.attach(self.label188, 2, 3, 0, 1, 0, 0, 0, 0)

        self.Limit = gtk.CheckButton()
        self.Limit.set_active(False)
        self.Limit.set_label(_("Limit uploads speed to"))
        self.Limit.show()
        self.Limit.connect("toggled", self.OnLimitToggled)
        self.table1.attach(self.Limit, 0, 1, 0, 1, 0, 0, 0, 0)

        self.LimitPerTransfer = gtk.RadioButton()
        self.LimitPerTransfer.set_active(False)
        self.LimitPerTransfer.set_label(_("per transfer"))
        self.LimitPerTransfer.show()

        self.table1.attach(self.LimitPerTransfer, 3, 4, 0, 1, gtk.FILL, 0, 0, 0)

        self.LimitTotalTransfers = gtk.RadioButton(self.LimitPerTransfer)
        self.LimitTotalTransfers.set_active(False)
        self.LimitTotalTransfers.set_label(_("total transfers"))
        self.LimitTotalTransfers.show()

        self.table1.attach(self.LimitTotalTransfers, 3, 4, 1, 2, gtk.FILL, 0, 0, 0)

        self.vbox81.pack_start(self.table1, False, False, 0)

        self.hbox171 = gtk.HBox(False, 5)
        self.hbox171.show()
        self.hbox171.set_spacing(5)

        self.label295 = gtk.Label(_("Upload Queue type:"))
        self.label295.set_padding(5, 0)
        self.label295.set_line_wrap(False)
        self.label295.show()
        self.hbox171.pack_start(self.label295, False, False, 0)

        self.RoundRobin = gtk.RadioButton()
        self.RoundRobin.set_active(False)
        self.RoundRobin.set_label(_("Round Robin"))
        self.RoundRobin.show()

        self.hbox171.pack_start(self.RoundRobin, False, False, 0)

        self.FirstInFirstOut = gtk.RadioButton(self.RoundRobin)
        self.FirstInFirstOut.set_active(False)
        self.FirstInFirstOut.set_label(_("First In, First Out"))
        self.FirstInFirstOut.show()

        self.hbox171.pack_start(self.FirstInFirstOut, False, False, 5)

        self.vbox81.pack_start(self.hbox171, False, True, 0)

        self.vbox83 = gtk.VBox(False, 0)
        self.vbox83.show()
        self.vbox83.set_spacing(0)

        self.hbox119 = gtk.HBox(False, 5)
        self.hbox119.show()
        self.hbox119.set_spacing(5)

        self.label189 = gtk.Label(_("Each user may queue a maximum of"))
        self.label189.set_alignment(0, 0.5)
        self.label189.set_padding(0, 0)
        self.label189.set_line_wrap(False)
        self.label189.show()
        self.hbox119.pack_start(self.label189, False, False, 0)

        self.MaxUserQueue = gtk.Entry()
        self.MaxUserQueue.set_size_request(35, -1)
        self.MaxUserQueue.set_text("100")
        self.MaxUserQueue.set_editable(True)
        self.MaxUserQueue.show()
        self.MaxUserQueue.set_visibility(True)
        self.hbox119.pack_start(self.MaxUserQueue, False, False, 0)

        self.label190 = gtk.Label(_("Megabytes"))
        self.label190.set_padding(0, 0)
        self.label190.set_line_wrap(False)
        self.label190.show()
        self.hbox119.pack_start(self.label190, False, False, 0)

        self.vbox83.pack_start(self.hbox119, False, False, 0)

        self.FriendsNoLimits = gtk.CheckButton()
        self.FriendsNoLimits.set_active(False)
        self.FriendsNoLimits.set_label(_("Queue size limit does not apply to friends"))
        self.FriendsNoLimits.show()
        self.vbox83.pack_start(self.FriendsNoLimits, False, False, 0)

        self.hbox165 = gtk.HBox(False, 0)
        self.hbox165.show()
        self.hbox165.set_spacing(0)

        self.DownloadLimit = gtk.CheckButton()
        self.DownloadLimit.set_active(False)
        self.DownloadLimit.set_label(_("Limit download speed to"))
        self.DownloadLimit.show()
        self.DownloadLimit.connect("toggled", self.OnDownloadLimitToggled)
        self.hbox165.pack_start(self.DownloadLimit, False, False, 0)

        self.DownloadLimitSpeed = gtk.Entry()
        self.DownloadLimitSpeed.set_size_request(30, -1)
        self.DownloadLimitSpeed.set_text("")
        self.DownloadLimitSpeed.set_editable(True)
        self.DownloadLimitSpeed.show()
        self.DownloadLimitSpeed.set_visibility(True)
        self.hbox165.pack_start(self.DownloadLimitSpeed, False, True, 0)

        self.label288 = gtk.Label(_("KBytes/sec"))
        self.label288.set_padding(0, 0)
        self.label288.set_line_wrap(False)
        self.label288.show()
        self.hbox165.pack_start(self.label288, False, False, 5)

        self.label289 = gtk.Label(_("for total transfers"))
        self.label289.set_padding(0, 0)
        self.label289.set_line_wrap(False)
        self.label289.show()
        self.hbox165.pack_start(self.label289, False, False, 0)

        self.vbox83.pack_start(self.hbox165, True, True, 0)

        self.vbox81.pack_start(self.vbox83, False, False, 0)

        self.hbox176 = gtk.HBox(False, 5)
        self.hbox176.show()
        self.hbox176.set_spacing(5)

        self.FriendsOnly = gtk.CheckButton()
        self.FriendsOnly.set_active(False)
        self.FriendsOnly.set_label(_("Share to friends only"))
        self.FriendsOnly.show()
        self.FriendsOnly.connect("toggled", self.OnFriendsOnlyToggled)
        self.hbox176.pack_start(self.FriendsOnly, False, False, 0)

        self.PreferFriends = gtk.CheckButton()
        self.PreferFriends.set_active(False)
        self.PreferFriends.set_label(_("Privilege all my friends"))
        self.PreferFriends.show()
        self.hbox176.pack_start(self.PreferFriends, False, False, 0)

        self.vbox81.pack_start(self.hbox176, False, False, 0)

        self.RemoteDownloads = gtk.CheckButton()
        self.RemoteDownloads.set_active(False)
        self.RemoteDownloads.set_label(_("Allow Buddies to send you files"))
        self.RemoteDownloads.show()
        self.vbox81.pack_start(self.RemoteDownloads, False, False, 0)

        self.LockIncoming = gtk.CheckButton()
        self.LockIncoming.set_active(False)
        self.LockIncoming.set_label(_("Lock incoming files (turn off for NFS)"))
        self.LockIncoming.show()
        self.vbox81.pack_start(self.LockIncoming, False, False, 0)

        self.ShowTransferButtons = gtk.CheckButton()
        self.ShowTransferButtons.set_active(False)
        self.ShowTransferButtons.set_label(_("Show Buttons in Transfers Tab"))
        self.ShowTransferButtons.show()
        self.vbox81.pack_start(self.ShowTransferButtons, False, False, 0)

        self.Main.add(self.vbox81)

        self.label183 = gtk.Label(_("Transfers"))
        self.label183.set_padding(0, 0)
        self.label183.set_line_wrap(False)
        self.label183.show()
        self.Main.set_label_widget(self.label183)


        if create:
            self.TransfersFrame.add(self.Main)

    def OnQueueUseSlotsToggled(self, widget):
        pass

    def OnLimitToggled(self, widget):
        pass

    def OnDownloadLimitToggled(self, widget):
        pass

    def OnFriendsOnlyToggled(self, widget):
        pass

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class UserinfoFrame:
    def __init__(self, create = True, accel_group = None):
        if accel_group is None:
             self.accel_group = gtk.AccelGroup()
        else:
             self.accel_group = accel_group
        if create:
            self.UserinfoFrame = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.UserinfoFrame.set_title(_("Userinfo"))
            self.UserinfoFrame.set_position(gtk.WIN_POS_NONE)
            self.UserinfoFrame.add_accel_group(self.accel_group)
            self.UserinfoFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()
        self.Main.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        self.vbox84 = gtk.VBox(False, 10)
        self.vbox84.show()
        self.vbox84.set_spacing(10)
        self.vbox84.set_border_width(5)

        self.vbox85 = gtk.VBox(False, 0)
        self.vbox85.show()
        self.vbox85.set_spacing(0)

        self.label193 = gtk.Label(_("Self description:"))
        self.label193.set_alignment(0, 0.5)
        self.label193.set_padding(0, 0)
        self.label193.set_line_wrap(False)
        self.label193.show()
        self.vbox85.pack_start(self.label193, False, False, 0)

        self.hbox121 = gtk.HBox(False, 0)
        self.hbox121.show()
        self.hbox121.set_spacing(0)

        self.scrolledwindow9 = gtk.ScrolledWindow()
        self.scrolledwindow9.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolledwindow9.set_size_request(250, -1)
        self.scrolledwindow9.show()
        self.scrolledwindow9.set_shadow_type(gtk.SHADOW_IN)

        self.Description = gtk.TextView()
        self.Description.set_wrap_mode(gtk.WRAP_WORD)
        self.Description.set_cursor_visible(True)
        self.Description.set_editable(True)
        self.Description.show()
        self.scrolledwindow9.add(self.Description)

        self.hbox121.pack_start(self.scrolledwindow9, False, False, 0)

        self.vbox85.pack_start(self.hbox121, True, True, 0)

        self.vbox84.pack_start(self.vbox85, True, True, 0)

        self.label265 = gtk.Label(_("Image:"))
        self.label265.set_alignment(0, 0.5)
        self.label265.set_padding(0, 0)
        self.label265.set_line_wrap(False)
        self.label265.show()
        self.vbox84.pack_start(self.label265, False, False, 0)

        self.hbox122 = gtk.HBox(False, 5)
        self.hbox122.show()
        self.hbox122.set_spacing(5)

        self.Image = gtk.Entry()
        self.Image.set_size_request(250, -1)
        self.Image.set_text("")
        self.Image.set_editable(True)
        self.Image.show()
        self.Image.set_visibility(True)
        self.hbox122.pack_start(self.Image, False, False, 0)

        self.button53 = gtk.Button()
        self.button53.show()
        self.button53.connect("clicked", self.OnChooseImage)

        self.alignment57 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment57.show()

        self.hbox151 = gtk.HBox(False, 2)
        self.hbox151.show()
        self.hbox151.set_spacing(2)

        self.image54 = gtk.Image()
        self.image54.set_padding(0, 0)
        self.image54.set_from_stock(gtk.STOCK_OPEN, 4)
        self.image54.show()
        self.hbox151.pack_start(self.image54, False, False, 0)

        self.label230 = gtk.Label(_("Choose..."))
        self.label230.set_padding(0, 0)
        self.label230.set_line_wrap(False)
        self.label230.show()
        self.hbox151.pack_start(self.label230, False, False, 0)

        self.alignment57.add(self.hbox151)

        self.button53.add(self.alignment57)

        self.hbox122.pack_start(self.button53, False, False, 0)

        self.vbox84.pack_start(self.hbox122, False, False, 0)

        self.Main.add(self.vbox84)

        self.label192 = gtk.Label(_("Personal settings"))
        self.label192.set_padding(0, 0)
        self.label192.set_line_wrap(False)
        self.label192.show()
        self.Main.set_label_widget(self.label192)


        if create:
            self.UserinfoFrame.add(self.Main)

    def OnChooseImage(self, widget):
        pass

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class BloatFrame:
    def __init__(self, create = True, accel_group = None):
        if accel_group is None:
             self.accel_group = gtk.AccelGroup()
        else:
             self.accel_group = accel_group
        if create:
            self.BloatFrame = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.BloatFrame.set_title(_("Bloat"))
            self.BloatFrame.set_position(gtk.WIN_POS_NONE)
            self.BloatFrame.add_accel_group(self.accel_group)
            self.BloatFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()
        self.Main.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        self.vbox86 = gtk.VBox(False, 5)
        self.vbox86.show()
        self.vbox86.set_spacing(5)
        self.vbox86.set_border_width(5)

        self.TabClosers = gtk.CheckButton()
        self.TabClosers.set_active(False)
        self.TabClosers.set_label(_("Close-buttons on tabs (requires restart)"))
        self.TabClosers.show()
        self.vbox86.pack_start(self.TabClosers, False, False, 0)

        self.hbox170 = gtk.HBox(False, 0)
        self.hbox170.show()
        self.hbox170.set_spacing(0)

        self.label294 = gtk.Label(_("Icon Theme Directory (requires restart):"))
        self.label294.set_padding(0, 0)
        self.label294.set_line_wrap(False)
        self.label294.show()
        self.hbox170.pack_start(self.label294, False, False, 0)

        self.vbox86.pack_start(self.hbox170, False, False, 0)

        self.hbox169 = gtk.HBox(False, 8)
        self.hbox169.show()
        self.hbox169.set_spacing(8)

        self.IconTheme = gtk.Entry()
        self.IconTheme.set_text("")
        self.IconTheme.set_editable(True)
        self.IconTheme.show()
        self.IconTheme.set_visibility(True)
        self.hbox169.pack_start(self.IconTheme, True, True, 0)

        self.ThemeButton = gtk.Button()
        self.ThemeButton.show()

        self.alignment73 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment73.show()

        self.hbox173 = gtk.HBox(False, 2)
        self.hbox173.show()
        self.hbox173.set_spacing(2)

        self.image67 = gtk.Image()
        self.image67.set_padding(0, 0)
        self.image67.set_from_stock(gtk.STOCK_DIRECTORY, 4)
        self.image67.show()
        self.hbox173.pack_start(self.image67, False, False, 0)

        self.label296 = gtk.Label(_("Select Theme"))
        self.label296.set_padding(0, 0)
        self.label296.set_line_wrap(False)
        self.label296.show()
        self.hbox173.pack_start(self.label296, False, False, 0)

        self.alignment73.add(self.hbox173)

        self.ThemeButton.add(self.alignment73)

        self.hbox169.pack_end(self.ThemeButton, False, False, 0)

        self.vbox86.pack_start(self.hbox169, False, True, 0)

        self.hbox172 = gtk.HBox(False, 0)
        self.hbox172.show()
        self.hbox172.set_spacing(0)

        self.chatfontlabel = gtk.Label(_("Chat Font:"))
        self.chatfontlabel.set_padding(5, 0)
        self.chatfontlabel.set_line_wrap(False)
        self.chatfontlabel.show()
        self.hbox172.pack_start(self.chatfontlabel, False, False, 0)

        self.SelectChatFont = gtk.FontButton()
        self.SelectChatFont.show()
        self.hbox172.pack_start(self.SelectChatFont, False, False, 5)

        self.vbox86.pack_start(self.hbox172, False, True, 0)

        self.table2 = gtk.Table()
        self.table2.show()
        self.table2.set_row_spacings(0)
        self.table2.set_col_spacings(15)

        self.PickLocal = gtk.Button()
        self.PickLocal.show()

        self.alignment43 = gtk.Alignment(0, 0.5, 0, 0)
        self.alignment43.show()

        self.hbox132 = gtk.HBox(False, 2)
        self.hbox132.show()
        self.hbox132.set_spacing(2)
        self.hbox132.set_border_width(3)

        self.image40 = gtk.Image()
        self.image40.set_padding(0, 0)
        self.image40.set_from_stock(gtk.STOCK_SELECT_COLOR, 4)
        self.image40.show()
        self.hbox132.pack_start(self.image40, False, False, 0)

        self.label205 = gtk.Label(_("Local text"))
        self.label205.set_padding(0, 0)
        self.label205.set_line_wrap(False)
        self.label205.show()
        self.hbox132.pack_start(self.label205, False, False, 0)

        self.alignment43.add(self.hbox132)

        self.PickLocal.add(self.alignment43)

        self.table2.attach(self.PickLocal, 0, 1, 2, 3, gtk.FILL, 0, 0, 0)

        self.PickMe = gtk.Button()
        self.PickMe.show()

        self.alignment44 = gtk.Alignment(0, 0.5, 0, 0)
        self.alignment44.show()

        self.hbox133 = gtk.HBox(False, 2)
        self.hbox133.show()
        self.hbox133.set_spacing(2)
        self.hbox133.set_border_width(3)

        self.image41 = gtk.Image()
        self.image41.set_padding(0, 0)
        self.image41.set_from_stock(gtk.STOCK_SELECT_COLOR, 4)
        self.image41.show()
        self.hbox133.pack_start(self.image41, False, False, 0)

        self.label206 = gtk.Label(_("/me text"))
        self.label206.set_padding(0, 0)
        self.label206.set_line_wrap(False)
        self.label206.show()
        self.hbox133.pack_start(self.label206, False, False, 0)

        self.alignment44.add(self.hbox133)

        self.PickMe.add(self.alignment44)

        self.table2.attach(self.PickMe, 0, 1, 3, 4, gtk.FILL, 0, 0, 0)

        self.PickHighlight = gtk.Button()
        self.PickHighlight.show()

        self.alignment45 = gtk.Alignment(0, 0.5, 0, 0)
        self.alignment45.show()

        self.hbox134 = gtk.HBox(False, 2)
        self.hbox134.show()
        self.hbox134.set_spacing(2)
        self.hbox134.set_border_width(3)

        self.image42 = gtk.Image()
        self.image42.set_padding(0, 0)
        self.image42.set_from_stock(gtk.STOCK_SELECT_COLOR, 4)
        self.image42.show()
        self.hbox134.pack_start(self.image42, False, False, 0)

        self.label207 = gtk.Label(_("Highlight text"))
        self.label207.set_padding(0, 0)
        self.label207.set_line_wrap(False)
        self.label207.show()
        self.hbox134.pack_start(self.label207, False, False, 0)

        self.alignment45.add(self.hbox134)

        self.PickHighlight.add(self.alignment45)

        self.table2.attach(self.PickHighlight, 0, 1, 4, 5, gtk.FILL, 0, 0, 0)

        self.DefaultMe = gtk.Button()
        self.DefaultMe.show()

        self.alignment41 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment41.show()

        self.hbox130 = gtk.HBox(False, 2)
        self.hbox130.show()
        self.hbox130.set_spacing(2)

        self.image38 = gtk.Image()
        self.image38.set_padding(0, 0)
        self.image38.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image38.show()
        self.hbox130.pack_start(self.image38, False, False, 0)

        self.label203 = gtk.Label(_("Default"))
        self.label203.set_padding(0, 0)
        self.label203.set_line_wrap(False)
        self.label203.show()
        self.hbox130.pack_start(self.label203, False, False, 0)

        self.alignment41.add(self.hbox130)

        self.DefaultMe.add(self.alignment41)

        self.table2.attach(self.DefaultMe, 2, 3, 3, 4, gtk.FILL, 0, 0, 0)

        self.DefaultHighlight = gtk.Button()
        self.DefaultHighlight.show()

        self.alignment42 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment42.show()

        self.hbox131 = gtk.HBox(False, 2)
        self.hbox131.show()
        self.hbox131.set_spacing(2)

        self.image39 = gtk.Image()
        self.image39.set_padding(0, 0)
        self.image39.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image39.show()
        self.hbox131.pack_start(self.image39, False, False, 0)

        self.label204 = gtk.Label(_("Default"))
        self.label204.set_padding(0, 0)
        self.label204.set_line_wrap(False)
        self.label204.show()
        self.hbox131.pack_start(self.label204, False, False, 0)

        self.alignment42.add(self.hbox131)

        self.DefaultHighlight.add(self.alignment42)

        self.table2.attach(self.DefaultHighlight, 2, 3, 4, 5, gtk.FILL, 0, 0, 0)

        self.Me = gtk.Entry()
        self.Me.set_text("")
        self.Me.set_editable(False)
        self.Me.show()
        self.Me.set_visibility(True)
        self.table2.attach(self.Me, 1, 2, 3, 4, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.Highlight = gtk.Entry()
        self.Highlight.set_text("")
        self.Highlight.set_editable(False)
        self.Highlight.show()
        self.Highlight.set_visibility(True)
        self.table2.attach(self.Highlight, 1, 2, 4, 5, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.PickImmediate = gtk.Button()
        self.PickImmediate.show()

        self.alignment46 = gtk.Alignment(0, 0.5, 0, 0)
        self.alignment46.show()

        self.hbox135 = gtk.HBox(False, 2)
        self.hbox135.show()
        self.hbox135.set_spacing(2)
        self.hbox135.set_border_width(3)

        self.image43 = gtk.Image()
        self.image43.set_padding(0, 0)
        self.image43.set_from_stock(gtk.STOCK_SELECT_COLOR, 4)
        self.image43.show()
        self.hbox135.pack_start(self.image43, False, False, 0)

        self.label209 = gtk.Label(_("Immediate DL"))
        self.label209.set_padding(0, 0)
        self.label209.set_line_wrap(False)
        self.label209.show()
        self.hbox135.pack_start(self.label209, False, False, 0)

        self.alignment46.add(self.hbox135)

        self.PickImmediate.add(self.alignment46)

        self.table2.attach(self.PickImmediate, 0, 1, 6, 7, gtk.FILL, 0, 0, 0)

        self.PickQueue = gtk.Button()
        self.PickQueue.show()

        self.alignment47 = gtk.Alignment(0, 0.5, 0, 0)
        self.alignment47.show()

        self.hbox136 = gtk.HBox(False, 2)
        self.hbox136.show()
        self.hbox136.set_spacing(2)
        self.hbox136.set_border_width(3)

        self.image44 = gtk.Image()
        self.image44.set_padding(0, 0)
        self.image44.set_from_stock(gtk.STOCK_SELECT_COLOR, 4)
        self.image44.show()
        self.hbox136.pack_start(self.image44, False, False, 0)

        self.label210 = gtk.Label(_("With queue"))
        self.label210.set_padding(0, 0)
        self.label210.set_line_wrap(False)
        self.label210.show()
        self.hbox136.pack_start(self.label210, False, False, 0)

        self.alignment47.add(self.hbox136)

        self.PickQueue.add(self.alignment47)

        self.table2.attach(self.PickQueue, 0, 1, 7, 8, gtk.FILL, 0, 0, 0)

        self.Immediate = gtk.Entry()
        self.Immediate.set_text("")
        self.Immediate.set_editable(False)
        self.Immediate.show()
        self.Immediate.set_visibility(True)
        self.table2.attach(self.Immediate, 1, 2, 6, 7, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.Queue = gtk.Entry()
        self.Queue.set_text("")
        self.Queue.set_editable(False)
        self.Queue.show()
        self.Queue.set_visibility(True)
        self.table2.attach(self.Queue, 1, 2, 7, 8, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.DefaultImmediate = gtk.Button()
        self.DefaultImmediate.show()

        self.alignment48 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment48.show()

        self.hbox137 = gtk.HBox(False, 2)
        self.hbox137.show()
        self.hbox137.set_spacing(2)

        self.image45 = gtk.Image()
        self.image45.set_padding(0, 0)
        self.image45.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image45.show()
        self.hbox137.pack_start(self.image45, False, False, 0)

        self.label211 = gtk.Label(_("Default"))
        self.label211.set_padding(0, 0)
        self.label211.set_line_wrap(False)
        self.label211.show()
        self.hbox137.pack_start(self.label211, False, False, 0)

        self.alignment48.add(self.hbox137)

        self.DefaultImmediate.add(self.alignment48)

        self.table2.attach(self.DefaultImmediate, 2, 3, 6, 7, gtk.FILL, 0, 0, 0)

        self.DefaultQueue = gtk.Button()
        self.DefaultQueue.show()

        self.alignment49 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment49.show()

        self.hbox138 = gtk.HBox(False, 2)
        self.hbox138.show()
        self.hbox138.set_spacing(2)

        self.image46 = gtk.Image()
        self.image46.set_padding(0, 0)
        self.image46.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image46.show()
        self.hbox138.pack_start(self.image46, False, False, 0)

        self.label212 = gtk.Label(_("Default"))
        self.label212.set_padding(0, 0)
        self.label212.set_line_wrap(False)
        self.label212.show()
        self.hbox138.pack_start(self.label212, False, False, 0)

        self.alignment49.add(self.hbox138)

        self.DefaultQueue.add(self.alignment49)

        self.table2.attach(self.DefaultQueue, 2, 3, 7, 8, gtk.FILL, 0, 0, 0)

        self.label208 = gtk.Label(_("Search colours"))
        self.label208.set_alignment(0, 0.5)
        self.label208.set_padding(0, 5)
        self.label208.set_line_wrap(False)
        self.label208.show()
        self.table2.attach(self.label208, 0, 3, 5, 6, gtk.FILL, 0, 0, 0)

        self.Local = gtk.Entry()
        self.Local.set_text("")
        self.Local.set_editable(False)
        self.Local.show()
        self.Local.set_visibility(True)
        self.table2.attach(self.Local, 1, 2, 2, 3, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.DefaultLocal = gtk.Button()
        self.DefaultLocal.show()

        self.alignment40 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment40.show()

        self.hbox129 = gtk.HBox(False, 2)
        self.hbox129.show()
        self.hbox129.set_spacing(2)

        self.image37 = gtk.Image()
        self.image37.set_padding(0, 0)
        self.image37.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image37.show()
        self.hbox129.pack_start(self.image37, False, False, 0)

        self.label202 = gtk.Label(_("Default"))
        self.label202.set_padding(0, 0)
        self.label202.set_line_wrap(False)
        self.label202.show()
        self.hbox129.pack_start(self.label202, False, False, 0)

        self.alignment40.add(self.hbox129)

        self.DefaultLocal.add(self.alignment40)

        self.table2.attach(self.DefaultLocal, 2, 3, 2, 3, gtk.FILL, 0, 0, 0)

        self.DefaultRemote = gtk.Button()
        self.DefaultRemote.show()

        self.alignment36 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment36.show()

        self.hbox125 = gtk.HBox(False, 2)
        self.hbox125.show()
        self.hbox125.set_spacing(2)

        self.image33 = gtk.Image()
        self.image33.set_padding(0, 0)
        self.image33.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image33.show()
        self.hbox125.pack_start(self.image33, False, False, 0)

        self.label198 = gtk.Label(_("Default"))
        self.label198.set_padding(0, 0)
        self.label198.set_line_wrap(False)
        self.label198.show()
        self.hbox125.pack_start(self.label198, False, False, 0)

        self.alignment36.add(self.hbox125)

        self.DefaultRemote.add(self.alignment36)

        self.table2.attach(self.DefaultRemote, 2, 3, 1, 2, gtk.FILL, 0, 0, 0)

        self.Remote = gtk.Entry()
        self.Remote.set_text("")
        self.Remote.set_editable(False)
        self.Remote.show()
        self.Remote.set_visibility(True)
        self.table2.attach(self.Remote, 1, 2, 1, 2, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.PickRemote = gtk.Button()
        self.PickRemote.show()

        self.alignment35 = gtk.Alignment(0, 0.5, 0, 0)
        self.alignment35.show()

        self.hbox124 = gtk.HBox(False, 2)
        self.hbox124.show()
        self.hbox124.set_spacing(2)
        self.hbox124.set_border_width(3)

        self.image32 = gtk.Image()
        self.image32.set_padding(0, 0)
        self.image32.set_from_stock(gtk.STOCK_SELECT_COLOR, 4)
        self.image32.show()
        self.hbox124.pack_start(self.image32, False, False, 0)

        self.label197 = gtk.Label(_("Remote text"))
        self.label197.set_padding(0, 0)
        self.label197.set_line_wrap(False)
        self.label197.show()
        self.hbox124.pack_start(self.label197, False, False, 0)

        self.alignment35.add(self.hbox124)

        self.PickRemote.add(self.alignment35)

        self.table2.attach(self.PickRemote, 0, 1, 1, 2, gtk.FILL, 0, 0, 0)

        self.label300 = gtk.Label(_("Chat colours"))
        self.label300.set_alignment(0, 0.5)
        self.label300.set_padding(0, 5)
        self.label300.set_line_wrap(False)
        self.label300.show()
        self.table2.attach(self.label300, 0, 3, 0, 1, gtk.FILL, 0, 0, 0)

        self.vbox86.pack_start(self.table2, False, False, 0)

        self.hbox139 = gtk.HBox(False, 5)
        self.hbox139.show()
        self.hbox139.set_spacing(5)

        self.label213 = gtk.Label(_("Decimal seperator:"))
        self.label213.set_alignment(0, 0.5)
        self.label213.set_padding(0, 0)
        self.label213.set_line_wrap(False)
        self.label213.show()
        self.hbox139.pack_start(self.label213, False, False, 0)

        self.DecimalSep_List = gtk.ListStore(gobject.TYPE_STRING)
        self.DecimalSep = gtk.ComboBoxEntry()
        self.DecimalSep.set_size_request(99, -1)
        self.DecimalSep.show()

        self.entry89 = self.DecimalSep.child
        self.entry89.set_text("")
        self.entry89.set_editable(False)
        self.entry89.show()
        self.entry89.set_visibility(True)

        self.DecimalSep.set_model(self.DecimalSep_List)
        self.DecimalSep.set_text_column(0)
        self.hbox139.pack_start(self.DecimalSep, False, False, 0)

        self.vbox86.pack_start(self.hbox139, False, False, 0)

        self.Main.add(self.vbox86)

        self.label195 = gtk.Label(_("Extra stuff for your comfort"))
        self.label195.set_padding(0, 0)
        self.label195.set_line_wrap(False)
        self.label195.show()
        self.Main.set_label_widget(self.label195)


        if create:
            self.BloatFrame.add(self.Main)

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class LogFrame:
    def __init__(self, create = True, accel_group = None):
        if accel_group is None:
             self.accel_group = gtk.AccelGroup()
        else:
             self.accel_group = accel_group
        if create:
            self.LogFrame = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.LogFrame.set_title(_("Log"))
            self.LogFrame.set_position(gtk.WIN_POS_NONE)
            self.LogFrame.add_accel_group(self.accel_group)
            self.LogFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()
        self.Main.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        self.vbox89 = gtk.VBox(False, 10)
        self.vbox89.show()
        self.vbox89.set_spacing(10)
        self.vbox89.set_border_width(5)

        self.LogPrivate = gtk.CheckButton()
        self.LogPrivate.set_active(False)
        self.LogPrivate.set_label(_("Log private chat by default"))
        self.LogPrivate.show()
        self.vbox89.pack_start(self.LogPrivate, False, False, 0)

        self.LogRooms = gtk.CheckButton()
        self.LogRooms.set_active(False)
        self.LogRooms.set_label(_("Log chatrooms by default"))
        self.LogRooms.show()
        self.vbox89.pack_start(self.LogRooms, False, False, 0)

        self.LogTransfers = gtk.CheckButton()
        self.LogTransfers.set_active(False)
        self.LogTransfers.set_label(_("Log transfers"))
        self.LogTransfers.show()
        self.vbox89.pack_start(self.LogTransfers, False, False, 0)

        self.vbox90 = gtk.VBox(False, 0)
        self.vbox90.show()
        self.vbox90.set_spacing(0)

        self.label217 = gtk.Label(_("Logs directory:"))
        self.label217.set_alignment(0, 0.5)
        self.label217.set_padding(0, 0)
        self.label217.set_line_wrap(False)
        self.label217.show()
        self.vbox90.pack_start(self.label217, False, False, 0)

        self.hbox140 = gtk.HBox(False, 5)
        self.hbox140.show()
        self.hbox140.set_spacing(5)

        self.LogDir = gtk.Entry()
        self.LogDir.set_text("~/")
        self.LogDir.set_editable(True)
        self.LogDir.show()
        self.LogDir.set_visibility(True)
        self.hbox140.pack_start(self.LogDir, False, False, 0)

        self.button66 = gtk.Button()
        self.button66.show()
        self.button66.connect("clicked", self.OnChooseLogDir)

        self.alignment54 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment54.show()

        self.hbox148 = gtk.HBox(False, 2)
        self.hbox148.show()
        self.hbox148.set_spacing(2)

        self.image51 = gtk.Image()
        self.image51.set_padding(0, 0)
        self.image51.set_from_stock(gtk.STOCK_OPEN, 4)
        self.image51.show()
        self.hbox148.pack_start(self.image51, False, False, 0)

        self.label227 = gtk.Label(_("Choose..."))
        self.label227.set_padding(0, 0)
        self.label227.set_line_wrap(False)
        self.label227.show()
        self.hbox148.pack_start(self.label227, False, False, 0)

        self.alignment54.add(self.hbox148)

        self.button66.add(self.alignment54)

        self.hbox140.pack_start(self.button66, False, False, 0)

        self.vbox90.pack_start(self.hbox140, False, False, 0)

        self.vbox89.pack_start(self.vbox90, False, False, 0)

        self.Main.add(self.vbox89)

        self.label216 = gtk.Label(_("Logging"))
        self.label216.set_padding(0, 0)
        self.label216.set_line_wrap(False)
        self.label216.show()
        self.Main.set_label_widget(self.label216)


        if create:
            self.LogFrame.add(self.Main)

    def OnChooseLogDir(self, widget):
        pass

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class BanFrame:
    def __init__(self, create = True, accel_group = None):
        if accel_group is None:
             self.accel_group = gtk.AccelGroup()
        else:
             self.accel_group = accel_group
        if create:
            self.BanFrame = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.BanFrame.set_title(_("Ban"))
            self.BanFrame.set_position(gtk.WIN_POS_NONE)
            self.BanFrame.add_accel_group(self.accel_group)
            self.BanFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()
        self.Main.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        self.vbox91 = gtk.VBox(False, 10)
        self.vbox91.show()
        self.vbox91.set_spacing(10)
        self.vbox91.set_border_width(5)

        self.hbox141 = gtk.HBox(False, 10)
        self.hbox141.show()
        self.hbox141.set_spacing(10)

        self.vbox92 = gtk.VBox(False, 0)
        self.vbox92.set_size_request(150, -1)
        self.vbox92.show()
        self.vbox92.set_spacing(0)

        self.label219 = gtk.Label(_("Banned Users:"))
        self.label219.set_padding(0, 0)
        self.label219.set_line_wrap(False)
        self.label219.show()
        self.vbox92.pack_start(self.label219, False, False, 0)

        self.scrolledwindow10 = gtk.ScrolledWindow()
        self.scrolledwindow10.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolledwindow10.show()
        self.scrolledwindow10.set_shadow_type(gtk.SHADOW_IN)

        self.Banned = gtk.TreeView()
        self.Banned.show()
        self.Banned.set_headers_visible(False)
        self.scrolledwindow10.add(self.Banned)

        self.vbox92.pack_start(self.scrolledwindow10, True, True, 0)

        self.button80 = gtk.Button()
        self.button80.show()
        self.button80.connect("clicked", self.OnAddBanned)

        self.alignment62 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment62.show()

        self.hbox156 = gtk.HBox(False, 2)
        self.hbox156.show()
        self.hbox156.set_spacing(2)

        self.image59 = gtk.Image()
        self.image59.set_padding(0, 0)
        self.image59.set_from_stock(gtk.STOCK_ADD, 4)
        self.image59.show()
        self.hbox156.pack_start(self.image59, False, False, 0)

        self.label238 = gtk.Label(_("Add..."))
        self.label238.set_padding(0, 0)
        self.label238.set_line_wrap(False)
        self.label238.show()
        self.hbox156.pack_start(self.label238, False, False, 0)

        self.alignment62.add(self.hbox156)

        self.button80.add(self.alignment62)

        self.vbox92.pack_start(self.button80, False, False, 0)

        self.button81 = gtk.Button()
        self.button81.show()
        self.button81.connect("clicked", self.OnRemoveBanned)

        self.alignment63 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment63.show()

        self.hbox157 = gtk.HBox(False, 2)
        self.hbox157.show()
        self.hbox157.set_spacing(2)

        self.image60 = gtk.Image()
        self.image60.set_padding(0, 0)
        self.image60.set_from_stock(gtk.STOCK_REMOVE, 4)
        self.image60.show()
        self.hbox157.pack_start(self.image60, False, False, 0)

        self.label239 = gtk.Label(_("Remove"))
        self.label239.set_padding(0, 0)
        self.label239.set_line_wrap(False)
        self.label239.show()
        self.hbox157.pack_start(self.label239, False, False, 0)

        self.alignment63.add(self.hbox157)

        self.button81.add(self.alignment63)

        self.vbox92.pack_start(self.button81, False, False, 0)

        self.button82 = gtk.Button()
        self.button82.show()
        self.button82.connect("clicked", self.OnClearBanned)

        self.alignment64 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment64.show()

        self.hbox158 = gtk.HBox(False, 2)
        self.hbox158.show()
        self.hbox158.set_spacing(2)

        self.image61 = gtk.Image()
        self.image61.set_padding(0, 0)
        self.image61.set_from_stock(gtk.STOCK_CLEAR, 4)
        self.image61.show()
        self.hbox158.pack_start(self.image61, False, False, 0)

        self.label240 = gtk.Label(_("Clear"))
        self.label240.set_padding(0, 0)
        self.label240.set_line_wrap(False)
        self.label240.show()
        self.hbox158.pack_start(self.label240, False, False, 0)

        self.alignment64.add(self.hbox158)

        self.button82.add(self.alignment64)

        self.vbox92.pack_start(self.button82, False, False, 0)

        self.hbox141.pack_start(self.vbox92, True, False, 0)

        self.vbox97 = gtk.VBox(False, 0)
        self.vbox97.set_size_request(150, -1)
        self.vbox97.show()
        self.vbox97.set_spacing(0)

        self.label237 = gtk.Label(_("Ignored users:"))
        self.label237.set_padding(0, 0)
        self.label237.set_line_wrap(False)
        self.label237.show()
        self.vbox97.pack_start(self.label237, False, False, 0)

        self.scrolledwindow13 = gtk.ScrolledWindow()
        self.scrolledwindow13.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolledwindow13.show()
        self.scrolledwindow13.set_shadow_type(gtk.SHADOW_IN)

        self.Ignored = gtk.TreeView()
        self.Ignored.show()
        self.Ignored.set_headers_visible(False)
        self.scrolledwindow13.add(self.Ignored)

        self.vbox97.pack_start(self.scrolledwindow13, True, True, 0)

        self.button77 = gtk.Button()
        self.button77.show()
        self.button77.connect("clicked", self.OnAddIgnored)

        self.alignment65 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment65.show()

        self.hbox159 = gtk.HBox(False, 2)
        self.hbox159.show()
        self.hbox159.set_spacing(2)

        self.image62 = gtk.Image()
        self.image62.set_padding(0, 0)
        self.image62.set_from_stock(gtk.STOCK_ADD, 4)
        self.image62.show()
        self.hbox159.pack_start(self.image62, False, False, 0)

        self.label241 = gtk.Label(_("Add..."))
        self.label241.set_padding(0, 0)
        self.label241.set_line_wrap(False)
        self.label241.show()
        self.hbox159.pack_start(self.label241, False, False, 0)

        self.alignment65.add(self.hbox159)

        self.button77.add(self.alignment65)

        self.vbox97.pack_start(self.button77, False, False, 0)

        self.button78 = gtk.Button()
        self.button78.show()
        self.button78.connect("clicked", self.OnRemoveIgnored)

        self.alignment66 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment66.show()

        self.hbox160 = gtk.HBox(False, 2)
        self.hbox160.show()
        self.hbox160.set_spacing(2)

        self.image63 = gtk.Image()
        self.image63.set_padding(0, 0)
        self.image63.set_from_stock(gtk.STOCK_REMOVE, 4)
        self.image63.show()
        self.hbox160.pack_start(self.image63, False, False, 0)

        self.label242 = gtk.Label(_("Remove"))
        self.label242.set_padding(0, 0)
        self.label242.set_line_wrap(False)
        self.label242.show()
        self.hbox160.pack_start(self.label242, False, False, 0)

        self.alignment66.add(self.hbox160)

        self.button78.add(self.alignment66)

        self.vbox97.pack_start(self.button78, False, False, 0)

        self.button79 = gtk.Button()
        self.button79.show()
        self.button79.connect("clicked", self.OnClearIgnored)

        self.alignment67 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment67.show()

        self.hbox161 = gtk.HBox(False, 2)
        self.hbox161.show()
        self.hbox161.set_spacing(2)

        self.image64 = gtk.Image()
        self.image64.set_padding(0, 0)
        self.image64.set_from_stock(gtk.STOCK_CLEAR, 4)
        self.image64.show()
        self.hbox161.pack_start(self.image64, False, False, 0)

        self.label243 = gtk.Label(_("Clear"))
        self.label243.set_padding(0, 0)
        self.label243.set_line_wrap(False)
        self.label243.show()
        self.hbox161.pack_start(self.label243, False, False, 0)

        self.alignment67.add(self.hbox161)

        self.button79.add(self.alignment67)

        self.vbox97.pack_start(self.button79, False, False, 0)

        self.hbox141.pack_start(self.vbox97, True, False, 0)

        self.vbox91.pack_start(self.hbox141, True, True, 0)

        self.hbox146 = gtk.HBox(False, 0)
        self.hbox146.show()
        self.hbox146.set_spacing(0)

        self.UseCustomBan = gtk.CheckButton()
        self.UseCustomBan.set_active(False)
        self.UseCustomBan.set_label(_("Use custom ban message:"))
        self.UseCustomBan.show()
        self.UseCustomBan.connect("toggled", self.OnUseCustomBanToggled)
        self.hbox146.pack_start(self.UseCustomBan, False, False, 0)

        self.CustomBan = gtk.Entry()
        self.CustomBan.set_text("")
        self.CustomBan.set_editable(True)
        self.CustomBan.show()
        self.CustomBan.set_visibility(True)
        self.hbox146.pack_start(self.CustomBan, True, True, 0)

        self.vbox91.pack_start(self.hbox146, False, False, 0)

        self.Main.add(self.vbox91)

        self.label218 = gtk.Label(_("Banning"))
        self.label218.set_padding(0, 0)
        self.label218.set_line_wrap(False)
        self.label218.show()
        self.Main.set_label_widget(self.label218)


        if create:
            self.BanFrame.add(self.Main)

    def OnAddBanned(self, widget):
        pass

    def OnRemoveBanned(self, widget):
        pass

    def OnClearBanned(self, widget):
        pass

    def OnAddIgnored(self, widget):
        pass

    def OnRemoveIgnored(self, widget):
        pass

    def OnClearIgnored(self, widget):
        pass

    def OnUseCustomBanToggled(self, widget):
        pass

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class SearchFrame:
    def __init__(self, create = True, accel_group = None):
        if accel_group is None:
             self.accel_group = gtk.AccelGroup()
        else:
             self.accel_group = accel_group
        if create:
            self.SearchFrame = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.SearchFrame.set_title(_("Search"))
            self.SearchFrame.set_position(gtk.WIN_POS_NONE)
            self.SearchFrame.add_accel_group(self.accel_group)
            self.SearchFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()
        self.Main.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        self.vbox93 = gtk.VBox(False, 10)
        self.vbox93.show()
        self.vbox93.set_spacing(10)
        self.vbox93.set_border_width(5)

        self.label262 = gtk.Label(_("Network Searches:"))
        self.label262.set_alignment(0, 0)
        self.label262.set_padding(0, 0)
        self.label262.set_line_wrap(False)
        self.label262.show()
        self.vbox93.pack_start(self.label262, False, False, 0)

        self.hbox147 = gtk.HBox(False, 5)
        self.hbox147.show()
        self.hbox147.set_spacing(5)

        self.label225 = gtk.Label(_("Send out a max of"))
        self.label225.set_alignment(1, 0.5)
        self.label225.set_padding(0, 0)
        self.label225.set_line_wrap(False)
        self.label225.show()
        self.hbox147.pack_start(self.label225, False, False, 0)

        self.MaxResults = gtk.Entry()
        self.MaxResults.set_size_request(28, -1)
        self.MaxResults.set_text("10")
        self.MaxResults.set_editable(True)
        self.MaxResults.show()
        self.MaxResults.set_visibility(True)
        self.hbox147.pack_start(self.MaxResults, False, False, 0)

        self.label226 = gtk.Label(_("results per search request"))
        self.label226.set_padding(0, 0)
        self.label226.set_line_wrap(False)
        self.label226.show()
        self.hbox147.pack_start(self.label226, False, False, 0)

        self.vbox93.pack_start(self.hbox147, False, False, 0)

        self.label263 = gtk.Label(_("Your Searches:"))
        self.label263.set_alignment(0, 0.5)
        self.label263.set_padding(0, 0)
        self.label263.set_line_wrap(False)
        self.label263.show()
        self.vbox93.pack_start(self.label263, False, False, 0)

        self.RegexpFilters = gtk.CheckButton()
        self.RegexpFilters.set_active(False)
        self.RegexpFilters.set_label(_("Use regular expressions for filter in & out"))
        self.RegexpFilters.show()
        self.vbox93.pack_start(self.RegexpFilters, False, False, 0)

        self.EnableFilters = gtk.CheckButton()
        self.EnableFilters.set_active(False)
        self.EnableFilters.set_label(_("Enable filters by default"))
        self.EnableFilters.show()
        self.EnableFilters.connect("toggled", self.OnEnableFiltersToggled)
        self.vbox93.pack_start(self.EnableFilters, False, False, 0)

        self.table4 = gtk.Table()
        self.table4.show()
        self.table4.set_row_spacings(5)
        self.table4.set_col_spacings(5)

        self.label255 = gtk.Label(_("Filter in:"))
        self.label255.set_alignment(0, 0.5)
        self.label255.set_padding(0, 0)
        self.label255.set_line_wrap(False)
        self.label255.show()
        self.table4.attach(self.label255, 0, 1, 0, 1, gtk.FILL, 0, 0, 0)

        self.label256 = gtk.Label(_("Filter out:"))
        self.label256.set_alignment(0, 0.5)
        self.label256.set_padding(0, 0)
        self.label256.set_line_wrap(False)
        self.label256.show()
        self.table4.attach(self.label256, 0, 1, 1, 2, gtk.FILL, 0, 0, 0)

        self.label257 = gtk.Label(_("Size:"))
        self.label257.set_alignment(0, 0.5)
        self.label257.set_padding(0, 0)
        self.label257.set_line_wrap(False)
        self.label257.show()
        self.table4.attach(self.label257, 0, 1, 2, 3, gtk.FILL, 0, 0, 0)

        self.label258 = gtk.Label(_("Bitrate:"))
        self.label258.set_alignment(0, 0.5)
        self.label258.set_padding(0, 0)
        self.label258.set_line_wrap(False)
        self.label258.show()
        self.table4.attach(self.label258, 0, 1, 3, 4, gtk.FILL, 0, 0, 0)

        self.FilterIn = gtk.Entry()
        self.FilterIn.set_text("")
        self.FilterIn.set_editable(True)
        self.FilterIn.show()
        self.FilterIn.set_visibility(True)
        self.table4.attach(self.FilterIn, 1, 2, 0, 1, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.FilterOut = gtk.Entry()
        self.FilterOut.set_text("")
        self.FilterOut.set_editable(True)
        self.FilterOut.show()
        self.FilterOut.set_visibility(True)
        self.table4.attach(self.FilterOut, 1, 2, 1, 2, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.hbox162 = gtk.HBox(False, 0)
        self.hbox162.show()
        self.hbox162.set_spacing(0)

        self.FilterSize = gtk.Entry()
        self.FilterSize.set_text("")
        self.FilterSize.set_editable(True)
        self.FilterSize.show()
        self.FilterSize.set_visibility(True)
        self.hbox162.pack_start(self.FilterSize, False, True, 0)

        self.table4.attach(self.hbox162, 1, 2, 2, 3, gtk.FILL, gtk.FILL, 0, 0)

        self.hbox163 = gtk.HBox(False, 0)
        self.hbox163.show()
        self.hbox163.set_spacing(0)

        self.FilterBR = gtk.Entry()
        self.FilterBR.set_text("")
        self.FilterBR.set_editable(True)
        self.FilterBR.show()
        self.FilterBR.set_visibility(True)
        self.hbox163.pack_start(self.FilterBR, False, True, 0)

        self.table4.attach(self.hbox163, 1, 2, 3, 4, gtk.FILL, gtk.FILL, 0, 0)

        self.FilterFree = gtk.CheckButton()
        self.FilterFree.set_active(False)
        self.FilterFree.set_label(_("Free slot"))
        self.FilterFree.show()
        self.table4.attach(self.FilterFree, 1, 2, 5, 6, gtk.FILL, 0, 0, 0)

        self.label259 = gtk.Label(_("Country:"))
        self.label259.set_alignment(0, 0.5)
        self.label259.set_padding(0, 0)
        self.label259.set_line_wrap(False)
        self.label259.show()
        self.table4.attach(self.label259, 0, 1, 4, 5, gtk.FILL, 0, 0, 0)

        self.hbox164 = gtk.HBox(False, 0)
        self.hbox164.show()
        self.hbox164.set_spacing(0)

        self.FilterCC = gtk.Entry()
        self.FilterCC.set_text("")
        self.FilterCC.set_editable(True)
        self.FilterCC.show()
        self.FilterCC.set_visibility(True)
        self.hbox164.pack_start(self.FilterCC, False, True, 0)

        self.table4.attach(self.hbox164, 1, 2, 4, 5, gtk.FILL, gtk.FILL, 0, 0)

        self.vbox93.pack_start(self.table4, True, True, 0)

        self.Main.add(self.vbox93)

        self.label224 = gtk.Label(_("Searches"))
        self.label224.set_padding(0, 0)
        self.label224.set_line_wrap(False)
        self.label224.show()
        self.Main.set_label_widget(self.label224)


        if create:
            self.SearchFrame.add(self.Main)

    def OnEnableFiltersToggled(self, widget):
        pass

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class SettingsWindow:
    def __init__(self, create = True, accel_group = None):
        if accel_group is None:
             self.accel_group = gtk.AccelGroup()
        else:
             self.accel_group = accel_group
        if create:
            self.SettingsWindow = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.SettingsWindow.set_default_size(600, 400)
            self.SettingsWindow.set_title(_("Nicotine Settings"))
            self.SettingsWindow.set_position(gtk.WIN_POS_CENTER)
            self.SettingsWindow.add_accel_group(self.accel_group)

        self.vbox94 = gtk.VBox(False, 10)
        self.vbox94.show()
        self.vbox94.set_spacing(10)
        self.vbox94.set_border_width(5)

        self.hpaned1 = gtk.HPaned()
        self.hpaned1.show()

        self.scrolledwindow11 = gtk.ScrolledWindow()
        self.scrolledwindow11.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolledwindow11.show()
        self.scrolledwindow11.set_shadow_type(gtk.SHADOW_IN)

        self.SettingsTreeview = gtk.TreeView()
        self.SettingsTreeview.set_size_request(150, -1)
        self.SettingsTreeview.show()
        self.SettingsTreeview.set_headers_visible(False)
        self.scrolledwindow11.add(self.SettingsTreeview)

        self.hpaned1.pack1(self.scrolledwindow11, False, True)

        self.scrolledwindow12 = gtk.ScrolledWindow()
        self.scrolledwindow12.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolledwindow12.show()
        self.scrolledwindow12.set_shadow_type(gtk.SHADOW_NONE)

        self.viewport1 = gtk.Viewport()
        self.viewport1.show()
        self.viewport1.set_shadow_type(gtk.SHADOW_NONE)

        self.scrolledwindow12.add(self.viewport1)

        self.hpaned1.pack2(self.scrolledwindow12, True, True)

        self.vbox94.pack_start(self.hpaned1, True, True, 0)

        self.hbuttonbox2 = gtk.HButtonBox()
        self.hbuttonbox2.show()
        self.hbuttonbox2.set_spacing(5)
        self.hbuttonbox2.set_layout(gtk.BUTTONBOX_END)

        self.button70 = gtk.Button(None, gtk.STOCK_APPLY)
        self.button70.show()
        self.button70.connect("clicked", self.OnApply)

        self.hbuttonbox2.pack_start(self.button70)

        self.button71 = gtk.Button(None, gtk.STOCK_OK)
        self.button71.show()
        self.button71.connect("clicked", self.OnOk)

        self.hbuttonbox2.pack_start(self.button71)

        self.button72 = gtk.Button(None, gtk.STOCK_CANCEL)
        self.button72.show()
        self.button72.connect("clicked", self.OnCancel)

        self.hbuttonbox2.pack_start(self.button72)

        self.vbox94.pack_start(self.hbuttonbox2, False, False, 0)


        if create:
            self.SettingsWindow.add(self.vbox94)

    def OnApply(self, widget):
        pass

    def OnOk(self, widget):
        pass

    def OnCancel(self, widget):
        pass

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class AwayFrame:
    def __init__(self, create = True, accel_group = None):
        if accel_group is None:
             self.accel_group = gtk.AccelGroup()
        else:
             self.accel_group = accel_group
        if create:
            self.AwayFrame = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.AwayFrame.set_title(_("Away"))
            self.AwayFrame.set_position(gtk.WIN_POS_NONE)
            self.AwayFrame.add_accel_group(self.accel_group)
            self.AwayFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()
        self.Main.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        self.vbox95 = gtk.VBox(False, 10)
        self.vbox95.show()
        self.vbox95.set_spacing(10)
        self.vbox95.set_border_width(5)

        self.hbox105 = gtk.HBox(False, 0)
        self.hbox105.show()
        self.hbox105.set_spacing(0)

        self.label170 = gtk.Label(_("Toggle away after "))
        self.label170.set_alignment(0, 0.5)
        self.label170.set_padding(0, 0)
        self.label170.set_line_wrap(False)
        self.label170.show()
        self.hbox105.pack_start(self.label170, False, False, 0)

        self.AutoAway = gtk.Entry()
        self.AutoAway.set_size_request(27, -1)
        self.AutoAway.set_text("15")
        self.AutoAway.set_editable(True)
        self.AutoAway.show()
        self.AutoAway.set_visibility(True)
        self.hbox105.pack_start(self.AutoAway, False, False, 0)

        self.label171 = gtk.Label(_(" minutes of inactivity"))
        self.label171.set_padding(0, 0)
        self.label171.set_line_wrap(False)
        self.label171.show()
        self.hbox105.pack_start(self.label171, False, False, 0)

        self.vbox95.pack_start(self.hbox105, False, True, 0)

        self.hbox107 = gtk.HBox(False, 0)
        self.hbox107.show()
        self.hbox107.set_spacing(0)

        self.label174 = gtk.Label(_("Auto-reply when away:  "))
        self.label174.set_alignment(0, 0.5)
        self.label174.set_padding(0, 0)
        self.label174.set_line_wrap(False)
        self.label174.show()
        self.hbox107.pack_start(self.label174, False, False, 0)

        self.AutoReply = gtk.Entry()
        self.AutoReply.set_size_request(193, -1)
        self.AutoReply.set_text("")
        self.AutoReply.set_editable(True)
        self.AutoReply.show()
        self.AutoReply.set_visibility(True)
        self.hbox107.pack_start(self.AutoReply, False, False, 0)

        self.vbox95.pack_start(self.hbox107, False, True, 0)

        self.Main.add(self.vbox95)

        self.label235 = gtk.Label(_("Away mode"))
        self.label235.set_padding(0, 0)
        self.label235.set_line_wrap(False)
        self.label235.show()
        self.Main.set_label_widget(self.label235)


        if create:
            self.AwayFrame.add(self.Main)

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class EventsFrame:
    def __init__(self, create = True, accel_group = None):
        if accel_group is None:
             self.accel_group = gtk.AccelGroup()
        else:
             self.accel_group = accel_group
        if create:
            self.EventsFrame = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.EventsFrame.set_title(_("Events"))
            self.EventsFrame.set_position(gtk.WIN_POS_NONE)
            self.EventsFrame.add_accel_group(self.accel_group)
            self.EventsFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()
        self.Main.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        self.vbox96 = gtk.VBox(False, 10)
        self.vbox96.show()
        self.vbox96.set_spacing(10)
        self.vbox96.set_border_width(5)

        self.vbox87 = gtk.VBox(False, 0)
        self.vbox87.show()
        self.vbox87.set_spacing(0)

        self.label214 = gtk.Label(_("Run command after download finishes ($ for filename):"))
        self.label214.set_alignment(0, 0.5)
        self.label214.set_padding(0, 0)
        self.label214.set_line_wrap(False)
        self.label214.show()
        self.vbox87.pack_start(self.label214, False, False, 0)

        self.AfterDownload = gtk.Entry()
        self.AfterDownload.set_size_request(313, -1)
        self.AfterDownload.set_text("")
        self.AfterDownload.set_editable(True)
        self.AfterDownload.show()
        self.AfterDownload.set_visibility(True)
        self.vbox87.pack_start(self.AfterDownload, False, False, 0)

        self.vbox96.pack_start(self.vbox87, False, False, 0)

        self.vbox88 = gtk.VBox(False, 0)
        self.vbox88.show()
        self.vbox88.set_spacing(0)

        self.label215 = gtk.Label(_("Run command after folder finishes ($ for folder path):"))
        self.label215.set_alignment(0, 0.5)
        self.label215.set_size_request(48, -1)
        self.label215.set_padding(0, 0)
        self.label215.set_line_wrap(False)
        self.label215.show()
        self.vbox88.pack_start(self.label215, False, False, 0)

        self.AfterFolder = gtk.Entry()
        self.AfterFolder.set_size_request(313, -1)
        self.AfterFolder.set_text("")
        self.AfterFolder.set_editable(True)
        self.AfterFolder.show()
        self.AfterFolder.set_visibility(True)
        self.vbox88.pack_start(self.AfterFolder, False, False, 0)

        self.vbox96.pack_start(self.vbox88, True, True, 0)

        self.PlayerLabel = gtk.Label(_("Audio Player command:"))
        self.PlayerLabel.set_padding(0, 0)
        self.PlayerLabel.set_line_wrap(False)
        self.PlayerLabel.show()
        self.vbox96.pack_start(self.PlayerLabel, False, False, 0)

        self.audioPlayerCombo_List = gtk.ListStore(gobject.TYPE_STRING)
        self.audioPlayerCombo = gtk.ComboBoxEntry()
        self.audioPlayerCombo.show()

        self.audioPlayerCombo.set_model(self.audioPlayerCombo_List)
        self.audioPlayerCombo.set_text_column(0)
        self.vbox96.pack_start(self.audioPlayerCombo, False, True, 0)

        self.Main.add(self.vbox96)

        self.label236 = gtk.Label(_("Events"))
        self.label236.set_padding(0, 0)
        self.label236.set_line_wrap(False)
        self.label236.show()
        self.Main.set_label_widget(self.label236)


        if create:
            self.EventsFrame.add(self.Main)

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class GeoBlockFrame:
    def __init__(self, create = True, accel_group = None):
        if accel_group is None:
             self.accel_group = gtk.AccelGroup()
        else:
             self.accel_group = accel_group
        if create:
            self.GeoBlockFrame = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.GeoBlockFrame.set_title(_("GeoBlock"))
            self.GeoBlockFrame.set_position(gtk.WIN_POS_NONE)
            self.GeoBlockFrame.add_accel_group(self.accel_group)
            self.GeoBlockFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()
        self.Main.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        self.vbox98 = gtk.VBox(False, 10)
        self.vbox98.show()
        self.vbox98.set_spacing(10)
        self.vbox98.set_border_width(5)

        self.GeoBlock = gtk.CheckButton()
        self.GeoBlock.set_active(False)
        self.GeoBlock.set_label(_("Enable geographical blocker"))
        self.GeoBlock.show()
        self.GeoBlock.connect("toggled", self.OnGeoBlockToggled)
        self.vbox98.pack_start(self.GeoBlock, False, False, 0)

        self.GeoPanic = gtk.CheckButton()
        self.GeoPanic.set_active(False)
        self.GeoPanic.set_label(_("Geographical paranoia (block unresolvable IPs)"))
        self.GeoPanic.show()
        self.vbox98.pack_start(self.GeoPanic, False, False, 0)

        self.label245 = gtk.Label(_("Country codes to block (comma separated):"))
        self.label245.set_alignment(0, 0.5)
        self.label245.set_padding(0, 0)
        self.label245.set_line_wrap(False)
        self.label245.show()
        self.vbox98.pack_start(self.label245, False, False, 0)

        self.GeoBlockCC = gtk.Entry()
        self.GeoBlockCC.set_text("")
        self.GeoBlockCC.set_editable(True)
        self.GeoBlockCC.show()
        self.GeoBlockCC.set_visibility(True)
        self.vbox98.pack_start(self.GeoBlockCC, False, False, 0)

        self.Main.add(self.vbox98)

        self.label244 = gtk.Label(_("Geographical Blocking"))
        self.label244.set_padding(0, 0)
        self.label244.set_line_wrap(False)
        self.label244.show()
        self.Main.set_label_widget(self.label244)


        if create:
            self.GeoBlockFrame.add(self.Main)

    def OnGeoBlockToggled(self, widget):
        pass

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class UrlCatchFrame:
    def __init__(self, create = True, accel_group = None):
        if accel_group is None:
             self.accel_group = gtk.AccelGroup()
        else:
             self.accel_group = accel_group
        if create:
            self.UrlCatchFrame = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.UrlCatchFrame.set_title(_("UrlCatch"))
            self.UrlCatchFrame.set_position(gtk.WIN_POS_NONE)
            self.UrlCatchFrame.add_accel_group(self.accel_group)
            self.UrlCatchFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()
        self.Main.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        self.vbox99 = gtk.VBox(False, 10)
        self.vbox99.show()
        self.vbox99.set_spacing(10)
        self.vbox99.set_border_width(5)

        self.URLCatching = gtk.CheckButton()
        self.URLCatching.set_active(False)
        self.URLCatching.set_label(_("Enable URL catching"))
        self.URLCatching.show()
        self.URLCatching.connect("toggled", self.OnURLCatchingToggled)
        self.vbox99.pack_start(self.URLCatching, False, False, 0)

        self.HumanizeURLs = gtk.CheckButton()
        self.HumanizeURLs.set_active(False)
        self.HumanizeURLs.set_label(_("Humanize slsk:// urls"))
        self.HumanizeURLs.show()
        self.vbox99.pack_start(self.HumanizeURLs, False, False, 0)

        self.label251 = gtk.Label(_("Protocols handlers:"))
        self.label251.set_padding(0, 0)
        self.label251.set_line_wrap(False)
        self.label251.show()
        self.vbox99.pack_start(self.label251, False, False, 0)

        self.scrolledwindow14 = gtk.ScrolledWindow()
        self.scrolledwindow14.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolledwindow14.show()
        self.scrolledwindow14.set_shadow_type(gtk.SHADOW_NONE)

        self.ProtocolHandlers = gtk.TreeView()
        self.ProtocolHandlers.show()
        self.ProtocolHandlers.set_headers_visible(True)
        self.scrolledwindow14.add(self.ProtocolHandlers)

        self.vbox99.pack_start(self.scrolledwindow14, True, True, 0)

        self.table3 = gtk.Table()
        self.table3.show()
        self.table3.set_row_spacings(0)
        self.table3.set_col_spacings(0)

        self.label252 = gtk.Label(_("Protocol:"))
        self.label252.set_alignment(0, 0.5)
        self.label252.set_padding(0, 0)
        self.label252.set_line_wrap(False)
        self.label252.show()
        self.table3.attach(self.label252, 0, 1, 0, 1, gtk.FILL, 0, 0, 0)

        self.Protocol = gtk.Entry()
        self.Protocol.set_text("")
        self.Protocol.set_editable(True)
        self.Protocol.show()
        self.Protocol.set_visibility(True)
        self.table3.attach(self.Protocol, 1, 2, 0, 1, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.label253 = gtk.Label(_("Handler:"))
        self.label253.set_alignment(0, 0.5)
        self.label253.set_padding(0, 0)
        self.label253.set_line_wrap(False)
        self.label253.show()
        self.table3.attach(self.label253, 0, 1, 1, 2, gtk.FILL, 0, 0, 0)

        self.Handler = gtk.Entry()
        self.Handler.set_text("")
        self.Handler.set_editable(True)
        self.Handler.show()
        self.Handler.set_visibility(True)
        self.table3.attach(self.Handler, 1, 2, 1, 2, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.button86 = gtk.Button()
        self.button86.show()
        self.button86.connect("clicked", self.OnUpdate)

        self.alignment74 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment74.show()

        self.hbox174 = gtk.HBox(False, 2)
        self.hbox174.show()
        self.hbox174.set_spacing(2)

        self.image68 = gtk.Image()
        self.image68.set_padding(0, 0)
        self.image68.set_from_stock(gtk.STOCK_REDO, 4)
        self.image68.show()
        self.hbox174.pack_start(self.image68, False, False, 0)

        self.label297 = gtk.Label(_("Update"))
        self.label297.set_padding(0, 0)
        self.label297.set_line_wrap(False)
        self.label297.show()
        self.hbox174.pack_start(self.label297, False, False, 0)

        self.alignment74.add(self.hbox174)

        self.button86.add(self.alignment74)

        self.table3.attach(self.button86, 2, 3, 0, 1, gtk.FILL, 0, 0, 0)

        self.button87 = gtk.Button()
        self.button87.show()
        self.button87.connect("clicked", self.OnRemove)

        self.alignment75 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment75.show()

        self.hbox175 = gtk.HBox(False, 2)
        self.hbox175.show()
        self.hbox175.set_spacing(2)

        self.image69 = gtk.Image()
        self.image69.set_padding(0, 0)
        self.image69.set_from_stock(gtk.STOCK_REMOVE, 4)
        self.image69.show()
        self.hbox175.pack_start(self.image69, False, False, 0)

        self.label298 = gtk.Label(_("Remove"))
        self.label298.set_padding(0, 0)
        self.label298.set_line_wrap(False)
        self.label298.show()
        self.hbox175.pack_start(self.label298, False, False, 0)

        self.alignment75.add(self.hbox175)

        self.button87.add(self.alignment75)

        self.table3.attach(self.button87, 2, 3, 1, 2, gtk.FILL, 0, 0, 0)

        self.vbox99.pack_start(self.table3, True, True, 0)

        self.Main.add(self.vbox99)

        self.label246 = gtk.Label(_("URL Catching:"))
        self.label246.set_padding(0, 0)
        self.label246.set_line_wrap(False)
        self.label246.show()
        self.Main.set_label_widget(self.label246)


        if create:
            self.UrlCatchFrame.add(self.Main)

    def OnURLCatchingToggled(self, widget):
        pass

    def OnUpdate(self, widget):
        pass

    def OnRemove(self, widget):
        pass

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class ConnectionFrame:
    def __init__(self, create = True, accel_group = None):
        if accel_group is None:
             self.accel_group = gtk.AccelGroup()
        else:
             self.accel_group = accel_group
        if create:
            self.ConnectionFrame = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.ConnectionFrame.set_title(_("Connection"))
            self.ConnectionFrame.set_position(gtk.WIN_POS_NONE)
            self.ConnectionFrame.add_accel_group(self.accel_group)
            self.ConnectionFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()
        self.Main.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        self.alignment68 = gtk.Alignment(0.5, 0.5, 1, 1)
        self.alignment68.show()

        self.vbox100 = gtk.VBox(False, 6)
        self.vbox100.show()
        self.vbox100.set_spacing(6)
        self.vbox100.set_border_width(2)

        self.label267 = gtk.Label(_("Choose Server to configure the server you wish to connect to, your username, password and connection ports."))
        self.label267.set_alignment(0, 0)
        self.label267.set_padding(8, 0)
        self.label267.set_line_wrap(True)
        self.label267.show()
        self.vbox100.pack_start(self.label267, False, False, 0)

        self.label268 = gtk.Label(_("Choose Shares to configure your Download and Shared directories."))
        self.label268.set_alignment(0, 0)
        self.label268.set_padding(8, 0)
        self.label268.set_line_wrap(True)
        self.label268.show()
        self.vbox100.pack_start(self.label268, False, False, 0)

        self.label269 = gtk.Label(_("Choose Transfers to configure how uploads are queued and what privileges are given to your friends."))
        self.label269.set_alignment(0, 0)
        self.label269.set_padding(8, 0)
        self.label269.set_line_wrap(True)
        self.label269.show()
        self.vbox100.pack_start(self.label269, False, False, 0)

        self.label284 = gtk.Label(_("Choose Geo Block (if available) to control from which countries users are allowed access to your shares."))
        self.label284.set_alignment(0, 0)
        self.label284.set_padding(8, 0)
        self.label284.set_line_wrap(True)
        self.label284.show()
        self.vbox100.pack_start(self.label284, False, False, 0)

        self.label285 = gtk.Label(_("If you wish to use Geo Block, install GeoIP and it's Python Bindings from your distro's packaging tool or from:"))
        self.label285.set_alignment(0, 0)
        self.label285.set_padding(8, 0)
        self.label285.set_line_wrap(True)
        self.label285.show()
        self.vbox100.pack_start(self.label285, False, False, 0)

        self.label286 = gtk.Label(_("http://www.maxmind.com/app/c"))
        self.label286.set_alignment(0, 0)
        self.label286.set_padding(8, 0)
        self.label286.set_line_wrap(False)
        self.label286.show()
        self.vbox100.pack_start(self.label286, False, False, 0)

        self.label287 = gtk.Label(_("http://www.maxmind.com/app/python"))
        self.label287.set_alignment(0, 0)
        self.label287.set_padding(8, 0)
        self.label287.set_line_wrap(False)
        self.label287.show()
        self.vbox100.pack_start(self.label287, False, False, 0)

        self.alignment68.add(self.vbox100)

        self.Main.add(self.alignment68)

        self.label266 = gtk.Label(_("Connection Settings"))
        self.label266.set_padding(0, 0)
        self.label266.set_line_wrap(False)
        self.label266.show()
        self.Main.set_label_widget(self.label266)


        if create:
            self.ConnectionFrame.add(self.Main)

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class UIFrame:
    def __init__(self, create = True, accel_group = None):
        if accel_group is None:
             self.accel_group = gtk.AccelGroup()
        else:
             self.accel_group = accel_group
        if create:
            self.UIFrame = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.UIFrame.set_title(_("UI"))
            self.UIFrame.set_position(gtk.WIN_POS_NONE)
            self.UIFrame.add_accel_group(self.accel_group)
            self.UIFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()
        self.Main.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        self.alignment69 = gtk.Alignment(0, 0, 1, 1)
        self.alignment69.show()

        self.vbox101 = gtk.VBox(False, 6)
        self.vbox101.show()
        self.vbox101.set_spacing(6)
        self.vbox101.set_border_width(2)

        self.label272 = gtk.Label(_("Choose Interface to configure text color and other settings."))
        self.label272.set_alignment(0, 0)
        self.label272.set_padding(8, 0)
        self.label272.set_line_wrap(True)
        self.label272.show()
        self.vbox101.pack_start(self.label272, False, False, 0)

        self.label273 = gtk.Label(_("Choose URL Catching to configure the programs used when clicking on links."))
        self.label273.set_alignment(0, 0)
        self.label273.set_padding(8, 0)
        self.label273.set_line_wrap(True)
        self.label273.show()
        self.vbox101.pack_start(self.label273, False, False, 0)

        self.alignment69.add(self.vbox101)

        self.Main.add(self.alignment69)

        self.label276 = gtk.Label(_("User Interface Settings"))
        self.label276.set_padding(0, 0)
        self.label276.set_line_wrap(False)
        self.label276.show()
        self.Main.set_label_widget(self.label276)


        if create:
            self.UIFrame.add(self.Main)

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class MiscFrame:
    def __init__(self, create = True, accel_group = None):
        if accel_group is None:
             self.accel_group = gtk.AccelGroup()
        else:
             self.accel_group = accel_group
        if create:
            self.MiscFrame = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.MiscFrame.set_title(_("Misc"))
            self.MiscFrame.set_position(gtk.WIN_POS_NONE)
            self.MiscFrame.add_accel_group(self.accel_group)
            self.MiscFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()
        self.Main.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        self.alignment70 = gtk.Alignment(0, 0, 1, 1)
        self.alignment70.show()

        self.vbox102 = gtk.VBox(False, 6)
        self.vbox102.show()
        self.vbox102.set_spacing(6)
        self.vbox102.set_border_width(2)

        self.label277 = gtk.Label(_("Choose Away mode to configure your auto-away settings."))
        self.label277.set_alignment(0, 0)
        self.label277.set_padding(8, 0)
        self.label277.set_line_wrap(True)
        self.label277.show()
        self.vbox102.pack_start(self.label277, False, False, 0)

        self.label278 = gtk.Label(_("Choose User info to add text and an image to your personal info."))
        self.label278.set_alignment(0, 0)
        self.label278.set_padding(8, 0)
        self.label278.set_line_wrap(True)
        self.label278.show()
        self.vbox102.pack_start(self.label278, False, False, 0)

        self.label280 = gtk.Label(_("Choose Ban / ignore to manage your ban list and ignore list."))
        self.label280.set_alignment(0, 0)
        self.label280.set_padding(8, 0)
        self.label280.set_line_wrap(True)
        self.label280.show()
        self.vbox102.pack_start(self.label280, False, False, 0)

        self.label281 = gtk.Label(_("Choose Logging to configure what's logged and where to save the logs."))
        self.label281.set_alignment(0, 0)
        self.label281.set_padding(8, 0)
        self.label281.set_line_wrap(True)
        self.label281.show()
        self.vbox102.pack_start(self.label281, False, False, 0)

        self.label282 = gtk.Label(_("Choose Searches to configure search settings and to set default search filters."))
        self.label282.set_alignment(0, 0)
        self.label282.set_padding(8, 0)
        self.label282.set_line_wrap(True)
        self.label282.show()
        self.vbox102.pack_start(self.label282, False, False, 0)

        self.label283 = gtk.Label(_("Choose Events to configure what commands are executed upon the completion of downloads."))
        self.label283.set_alignment(0, 0)
        self.label283.set_padding(8, 0)
        self.label283.set_line_wrap(True)
        self.label283.show()
        self.vbox102.pack_start(self.label283, False, False, 0)

        self.alignment70.add(self.vbox102)

        self.Main.add(self.alignment70)

        self.label279 = gtk.Label(_("Miscellaneous Settings"))
        self.label279.set_padding(0, 0)
        self.label279.set_line_wrap(False)
        self.label279.show()
        self.Main.set_label_widget(self.label279)


        if create:
            self.MiscFrame.add(self.Main)

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

