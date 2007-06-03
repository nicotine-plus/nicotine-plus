import gtk, gobject
from pynicotine.utils import _

class ServerFrame:
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
            self.ServerFrame = gtk.Window()
            self.ServerFrame.set_title(_("Server Settings"))
            self.ServerFrame.add_accel_group(self.accel_group)
            self.ServerFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()

        self.vbox71 = gtk.VBox(False, 0)
        self.vbox71.show()
        self.vbox71.set_spacing(10)
        self.vbox71.set_border_width(5)

        self.vbox72 = gtk.VBox(False, 0)
        self.vbox72.show()

        self.label166 = gtk.Label(_("Server: (use server.slsknet.org:2240 for the main server)"))
        self.label166.set_alignment(0, 0)
        self.label166.set_size_request(360, -1)
        self.label166.set_line_wrap(True)
        self.label166.show()
        self.vbox72.pack_start(self.label166, False, False, 3)

        self.hbox103 = gtk.HBox(False, 0)
        self.hbox103.show()

        self.Server_List = gtk.ListStore(gobject.TYPE_STRING)
        self.Server = gtk.ComboBoxEntry()
        self.Server.set_size_request(200, -1)
        self.Server.show()

        self.comboboxentry_entry1 = self.Server.child

        self.Server.set_model(self.Server_List)
        self.Server.set_text_column(0)
        self.hbox103.pack_start(self.Server, False, False, 0)

        self.vbox72.pack_start(self.hbox103, False, False, 0)

        self.vbox71.pack_start(self.vbox72, False, True, 0)

        self.hbox104 = gtk.HBox(False, 0)
        self.hbox104.show()
        self.hbox104.set_spacing(10)

        self.vbox73 = gtk.VBox(False, 0)
        self.vbox73.show()

        self.label167 = gtk.Label(_("Login:"))
        self.label167.set_alignment(0, 0.50)
        self.label167.set_size_request(57, -1)
        self.label167.show()
        self.vbox73.pack_start(self.label167, False, False, 0)

        self.Login = gtk.Entry()
        self.Login.set_size_request(130, -1)
        self.Login.show()
        self.Login.set_width_chars(29)
        self.vbox73.pack_start(self.Login, False, False, 0)

        self.hbox104.pack_start(self.vbox73, False, False, 0)

        self.vseparator8 = gtk.VSeparator()
        self.vseparator8.show()
        self.hbox104.pack_start(self.vseparator8, False, False, 0)

        self.vbox74 = gtk.VBox(False, 0)
        self.vbox74.show()

        self.label168 = gtk.Label(_("Password:"))
        self.label168.set_alignment(0, 0)
        self.label168.set_size_request(5, -1)
        self.label168.show()
        self.vbox74.pack_start(self.label168, False, False, 0)

        self.Password = gtk.Entry()
        self.Password.set_size_request(100, -1)
        self.Password.show()
        self.Password.set_visibility(False)
        self.Password.set_width_chars(10)
        self.vbox74.pack_start(self.Password, False, False, 0)

        self.hbox104.pack_start(self.vbox74, False, False, 0)

        self.vbox71.pack_start(self.hbox104, False, True, 0)

        self.vbox75 = gtk.VBox(False, 0)
        self.vbox75.show()

        self.label169 = gtk.Label(_("Network Character Encoding (utf-8 is a good choice)"))
        self.label169.set_alignment(0, 0.50)
        self.label169.show()
        self.vbox75.pack_start(self.label169, False, False, 0)

        self.hbox108 = gtk.HBox(False, 0)
        self.hbox108.show()

        self.Encoding_List = gtk.ListStore(gobject.TYPE_STRING)
        self.Encoding = gtk.ComboBoxEntry()
        self.Encoding.set_size_request(100, -1)
        self.Encoding.show()

        self.comboboxentry_entry2 = self.Encoding.child

        self.Encoding.set_model(self.Encoding_List)
        self.Encoding.set_text_column(0)
        self.hbox108.pack_start(self.Encoding, False, False, 0)

        self.vbox75.pack_start(self.hbox108, False, False, 0)

        self.vbox71.pack_start(self.vbox75, False, True, 0)

        self.vbox76 = gtk.VBox(False, 0)
        self.vbox76.show()

        self.label172 = gtk.Label(_("Client connection ports (use first available):"))
        self.label172.set_alignment(0, 0.50)
        self.label172.show()
        self.vbox76.pack_start(self.label172, False, False, 0)

        self.hbox106 = gtk.HBox(False, 0)
        self.hbox106.set_size_request(114, -1)
        self.hbox106.show()
        self.hbox106.set_spacing(5)

        self.FirstPort = gtk.Entry()
        self.FirstPort.set_size_request(50, -1)
        self.FirstPort.set_text(_("2234"))
        self.FirstPort.show()
        self.hbox106.pack_start(self.FirstPort, False, False, 0)

        self.label173 = gtk.Label(_("-"))
        self.label173.set_size_request(0, -1)
        self.label173.show()
        self.hbox106.pack_start(self.label173, False, False, 0)

        self.LastPort = gtk.Entry()
        self.LastPort.set_size_request(50, -1)
        self.LastPort.set_text(_("2242"))
        self.LastPort.show()
        self.hbox106.pack_start(self.LastPort, False, False, 0)

        self.vbox76.pack_start(self.hbox106)

        self.label260 = gtk.Label(_("Use the above ports to configure your router or firewall."))
        self.label260.set_alignment(0, 0.50)
        self.label260.set_padding(0, 11)
        self.label260.show()
        self.vbox76.pack_start(self.label260, False, False, 0)

        self.DirectConnection = gtk.CheckButton()
        self.DirectConnection.set_label(_("I can receive direct connections"))
        self.DirectConnection.show()
        self.vbox76.pack_start(self.DirectConnection, False, False, 0)

        self.label271 = gtk.Label(_("(only use if the above ports are remotely accessable)"))
        self.label271.set_alignment(0, 0.50)
        self.label271.show()
        self.vbox76.pack_start(self.label271, False, False, 0)

        self.vbox71.pack_start(self.vbox76, False, False, 0)

        self.ctcptogglebutton = gtk.CheckButton()
        self.ctcptogglebutton.set_label(_("Enable CTCP-like PM responses (Client Version)"))
        self.ctcptogglebutton.show()
        self.vbox71.pack_start(self.ctcptogglebutton, False, False, 0)

        self.Main.add(self.vbox71)

        self.label165 = gtk.Label(_("Server"))
        self.label165.show()
        self.Main.set_label_widget(self.label165)


        if create:
            self.ServerFrame.add(self.Main)

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class SharesFrame:
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
            self.SharesFrame = gtk.Window()
            self.SharesFrame.set_title(_("Shares"))
            self.SharesFrame.add_accel_group(self.accel_group)
            self.SharesFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()

        self.vbox77 = gtk.VBox(False, 0)
        self.vbox77.show()
        self.vbox77.set_spacing(7)
        self.vbox77.set_border_width(5)

        self.vbox78 = gtk.VBox(False, 0)
        self.vbox78.show()

        self.label176 = gtk.Label(_("Incomplete file directory:"))
        self.label176.set_alignment(0, 0.50)
        self.label176.show()
        self.vbox78.pack_start(self.label176, False, False, 0)

        self.hbox109 = gtk.HBox(False, 0)
        self.hbox109.show()
        self.hbox109.set_spacing(5)

        self.IncompleteDir = gtk.Entry()
        self.IncompleteDir.set_size_request(250, -1)
        self.IncompleteDir.show()
        self.hbox109.pack_start(self.IncompleteDir)

        self.button73 = gtk.Button()
        self.button73.show()
        self.button73.connect("clicked", self.OnChooseIncompleteDir)

        self.alignment58 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment58.show()

        self.hbox152 = gtk.HBox(False, 0)
        self.hbox152.show()
        self.hbox152.set_spacing(2)

        self.image55 = gtk.Image()
        self.image55.set_from_stock(gtk.STOCK_OPEN, 4)
        self.image55.show()
        self.hbox152.pack_start(self.image55, False, False, 0)

        self.label231 = gtk.Label(_("Choose..."))
        self.label231.show()
        self.hbox152.pack_start(self.label231, False, False, 0)

        self.alignment58.add(self.hbox152)

        self.button73.add(self.alignment58)

        self.hbox109.pack_start(self.button73, False, False, 0)

        self.vbox78.pack_start(self.hbox109, False, False, 0)

        self.vbox77.pack_start(self.vbox78, False, False, 0)

        self.vbox79 = gtk.VBox(False, 0)
        self.vbox79.show()

        self.label178 = gtk.Label(_("Download directory:"))
        self.label178.set_alignment(0, 0.50)
        self.label178.show()
        self.vbox79.pack_start(self.label178, False, False, 0)

        self.hbox111 = gtk.HBox(False, 0)
        self.hbox111.show()
        self.hbox111.set_spacing(5)

        self.DownloadDir = gtk.Entry()
        self.DownloadDir.set_size_request(250, -1)
        self.DownloadDir.show()
        self.hbox111.pack_start(self.DownloadDir)

        self.button74 = gtk.Button()
        self.button74.show()
        self.button74.connect("clicked", self.OnChooseDownloadDir)

        self.alignment59 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment59.show()

        self.hbox153 = gtk.HBox(False, 0)
        self.hbox153.show()
        self.hbox153.set_spacing(2)

        self.image56 = gtk.Image()
        self.image56.set_from_stock(gtk.STOCK_OPEN, 4)
        self.image56.show()
        self.hbox153.pack_start(self.image56, False, False, 0)

        self.label232 = gtk.Label(_("Choose..."))
        self.label232.show()
        self.hbox153.pack_start(self.label232, False, False, 0)

        self.alignment59.add(self.hbox153)

        self.button74.add(self.alignment59)

        self.hbox111.pack_start(self.button74, False, False, 0)

        self.vbox79.pack_start(self.hbox111, False, False, 0)

        self.ShareDownloadDir = gtk.CheckButton()
        self.ShareDownloadDir.set_label(_("Share download directory"))
        self.ShareDownloadDir.show()
        self.ShareDownloadDir.connect("toggled", self.OnShareDownloadDirToggled)
        self.vbox79.pack_start(self.ShareDownloadDir, False, False, 0)

        self.vbox77.pack_start(self.vbox79, False, False, 0)

        self.RescanOnStartup = gtk.CheckButton()
        self.RescanOnStartup.set_label(_("Rescan shares on startup"))
        self.RescanOnStartup.show()
        self.vbox77.pack_start(self.RescanOnStartup, False, False, 0)

        self.hbox113 = gtk.HBox(False, 0)
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

        self.hbox113.pack_start(self.scrolledwindow8)

        self.vbox80 = gtk.VBox(False, 0)
        self.vbox80.show()

        self.addSharesButton = gtk.Button()
        self.addSharesButton.show()
        self.addSharesButton.connect("clicked", self.OnAddSharedDir)

        self.alignment60 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment60.show()

        self.hbox154 = gtk.HBox(False, 0)
        self.hbox154.show()
        self.hbox154.set_spacing(2)

        self.image57 = gtk.Image()
        self.image57.set_from_stock(gtk.STOCK_OPEN, 4)
        self.image57.show()
        self.hbox154.pack_start(self.image57, False, False, 0)

        self.label233 = gtk.Label(_("Add..."))
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

        self.hbox155 = gtk.HBox(False, 0)
        self.hbox155.show()
        self.hbox155.set_spacing(2)

        self.image58 = gtk.Image()
        self.image58.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image58.show()
        self.hbox155.pack_start(self.image58, False, False, 0)

        self.label234 = gtk.Label(_("Remove"))
        self.label234.show()
        self.hbox155.pack_start(self.label234, False, False, 0)

        self.alignment61.add(self.hbox155)

        self.removeSharesButton.add(self.alignment61)

        self.vbox80.pack_start(self.removeSharesButton, False, False, 0)

        self.hbox113.pack_start(self.vbox80, False, False, 0)

        self.vbox77.pack_start(self.hbox113)

        self.enableBuddyShares = gtk.CheckButton()
        self.enableBuddyShares.set_label(_("Enable Buddy-Only shares"))
        self.enableBuddyShares.show()
        self.enableBuddyShares.connect("toggled", self.OnEnabledBuddySharesToggled)
        self.vbox77.pack_start(self.enableBuddyShares, False, False, 0)

        self.hbox166 = gtk.HBox(False, 0)
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

        self.hbox166.pack_start(self.scrolledwindow15)

        self.vbox103 = gtk.VBox(False, 0)
        self.vbox103.show()

        self.addBuddySharesButton = gtk.Button()
        self.addBuddySharesButton.show()
        self.addBuddySharesButton.connect("clicked", self.OnAddSharedBuddyDir)

        self.alignment71 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment71.show()

        self.hbox167 = gtk.HBox(False, 0)
        self.hbox167.show()
        self.hbox167.set_spacing(2)

        self.image65 = gtk.Image()
        self.image65.set_from_stock(gtk.STOCK_OPEN, 4)
        self.image65.show()
        self.hbox167.pack_start(self.image65, False, False, 0)

        self.label290 = gtk.Label(_("Add..."))
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

        self.hbox168 = gtk.HBox(False, 0)
        self.hbox168.show()
        self.hbox168.set_spacing(2)

        self.image66 = gtk.Image()
        self.image66.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image66.show()
        self.hbox168.pack_start(self.image66, False, False, 0)

        self.label293 = gtk.Label(_("Remove"))
        self.label293.show()
        self.hbox168.pack_start(self.label293, False, False, 0)

        self.alignment72.add(self.hbox168)

        self.removeBuddySharesButton.add(self.alignment72)

        self.vbox103.pack_start(self.removeBuddySharesButton, False, False, 0)

        self.hbox166.pack_start(self.vbox103, False, False, 0)

        self.vbox77.pack_start(self.hbox166)

        self.Main.add(self.vbox77)

        self.label175 = gtk.Label(_("Shares"))
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
            self.TransfersFrame = gtk.Window()
            self.TransfersFrame.set_title(_("Transfers"))
            self.TransfersFrame.add_accel_group(self.accel_group)
            self.TransfersFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()

        self.vbox81 = gtk.VBox(False, 0)
        self.vbox81.show()
        self.vbox81.set_spacing(5)
        self.vbox81.set_border_width(5)

        self.expander5 = gtk.Expander()
        self.expander5.set_expanded(True)
        self.expander5.show()

        self.vbox114 = gtk.VBox(False, 0)
        self.vbox114.show()
        self.vbox114.set_spacing(3)

        self.hbox171 = gtk.HBox(False, 0)
        self.hbox171.show()
        self.hbox171.set_spacing(5)

        self.label295 = gtk.Label(_("Upload Queue type:"))
        self.label295.set_alignment(0, 0.50)
        self.label295.show()
        self.hbox171.pack_start(self.label295, False, False, 0)

        self.RoundRobin = gtk.RadioButton()
        self.tooltips.set_tip(self.RoundRobin, _("Users will be sent one file and then another user will be selected"))
        self.RoundRobin.set_label(_("Round Robin"))
        self.RoundRobin.show()

        self.hbox171.pack_start(self.RoundRobin, False, False, 0)

        self.FirstInFirstOut = gtk.RadioButton(self.RoundRobin)
        self.tooltips.set_tip(self.FirstInFirstOut, _("Files will be sent in the order they were queued"))
        self.FirstInFirstOut.set_label(_("First In, First Out"))
        self.FirstInFirstOut.show()

        self.hbox171.pack_start(self.FirstInFirstOut, False, False, 5)

        self.vbox114.pack_start(self.hbox171, False, False, 0)

        self.hbox117 = gtk.HBox(False, 0)
        self.hbox117.show()
        self.hbox117.set_spacing(5)

        self.label185 = gtk.Label(_("Queue Uploads if total transfer speed reaches"))
        self.label185.set_alignment(0, 0.50)
        self.label185.show()
        self.hbox117.pack_start(self.label185, False, False, 0)

        self.QueueBandwidth = gtk.Entry()
        self.QueueBandwidth.set_size_request(50, -1)
        self.QueueBandwidth.show()
        self.hbox117.pack_start(self.QueueBandwidth, False, False, 0)

        self.label186 = gtk.Label(_("KBytes/sec"))
        self.label186.set_line_wrap(True)
        self.label186.show()
        self.hbox117.pack_start(self.label186, False, False, 0)

        self.vbox114.pack_start(self.hbox117, False, False, 0)

        self.hbox118 = gtk.HBox(False, 0)
        self.hbox118.show()
        self.hbox118.set_spacing(5)

        self.QueueUseSlots = gtk.CheckButton()
        self.tooltips.set_tip(self.QueueUseSlots, _("If disabled, slots will automatically be determined by available bandwidth limitations"))
        self.QueueUseSlots.set_label(_("Limit number of upload slots to"))
        self.QueueUseSlots.show()
        self.QueueUseSlots.connect("toggled", self.OnQueueUseSlotsToggled)
        self.hbox118.pack_start(self.QueueUseSlots, False, False, 0)

        self.QueueSlots = gtk.Entry()
        self.QueueSlots.set_size_request(50, -1)
        self.tooltips.set_tip(self.QueueSlots, _("Set to 0 to disable uploads"))
        self.QueueSlots.show()
        self.hbox118.pack_start(self.QueueSlots, False, False, 0)

        self.label254 = gtk.Label(_("(NOT RECOMMENDED)"))
        self.label254.show()
        self.hbox118.pack_start(self.label254, False, False, 0)

        self.vbox114.pack_start(self.hbox118, False, False, 0)

        self.table1 = gtk.Table()
        self.table1.show()
        self.table1.set_col_spacings(5)

        self.LimitTotalTransfers = gtk.RadioButton()
        self.LimitTotalTransfers.set_label(_("total transfers"))
        self.LimitTotalTransfers.show()

        self.table1.attach(self.LimitTotalTransfers, 3, 4, 1, 2, gtk.FILL, 0, 0, 0)

        self.LimitPerTransfer = gtk.RadioButton(self.LimitTotalTransfers)
        self.LimitPerTransfer.set_label(_("per transfer"))
        self.LimitPerTransfer.show()

        self.table1.attach(self.LimitPerTransfer, 3, 4, 0, 1, gtk.FILL, 0, 0, 0)

        self.Limit = gtk.CheckButton()
        self.Limit.set_label(_("Limit uploads speed to"))
        self.Limit.show()
        self.Limit.connect("toggled", self.OnLimitToggled)
        self.table1.attach(self.Limit, 0, 1, 0, 1, 0, 0, 0, 0)

        self.label188 = gtk.Label(_("KBytes/sec"))
        self.label188.show()
        self.table1.attach(self.label188, 2, 3, 0, 1, 0, 0, 0, 0)

        self.LimitSpeed = gtk.Entry()
        self.LimitSpeed.set_size_request(50, -1)
        self.LimitSpeed.show()
        self.table1.attach(self.LimitSpeed, 1, 2, 0, 1, 0, 0, 0, 0)

        self.vbox114.pack_start(self.table1, False, False, 0)

        self.hbox119 = gtk.HBox(False, 0)
        self.hbox119.show()
        self.hbox119.set_spacing(5)

        self.label189 = gtk.Label(_("Each user may queue a maximum of"))
        self.label189.set_alignment(0, 0.50)
        self.label189.show()
        self.hbox119.pack_start(self.label189, False, False, 0)

        self.MaxUserQueue = gtk.Entry()
        self.MaxUserQueue.set_size_request(50, -1)
        self.tooltips.set_tip(self.MaxUserQueue, _("Files will remain in the download user's queue with a warning message but will not be added to your upload queue until the user retries them with a smaller total queue size"))
        self.MaxUserQueue.set_text(_("100"))
        self.MaxUserQueue.show()
        self.hbox119.pack_start(self.MaxUserQueue, False, False, 0)

        self.label190 = gtk.Label(_("Megabytes"))
        self.label190.show()
        self.hbox119.pack_start(self.label190, False, False, 0)

        self.vbox114.pack_start(self.hbox119, False, False, 0)

        self.FriendsNoLimits = gtk.CheckButton()
        self.FriendsNoLimits.set_label(_("Queue size limit does not apply to friends"))
        self.FriendsNoLimits.show()
        self.vbox114.pack_start(self.FriendsNoLimits, False, False, 0)

        self.hbox211 = gtk.HBox(False, 0)
        self.hbox211.show()
        self.hbox211.set_spacing(5)

        self.RemoteDownloads = gtk.CheckButton()
        self.tooltips.set_tip(self.RemoteDownloads, _("The users will be able to send you files. These files will be downloaded into the Buddy Uploads subdirectory in your Download directory"))
        self.RemoteDownloads.set_label(_("Allow these users to send you files:"))
        self.RemoteDownloads.show()
        self.hbox211.pack_start(self.RemoteDownloads, False, False, 0)

        self.UploadsAllowed_List = gtk.ListStore(gobject.TYPE_STRING)
        self.UploadsAllowed = gtk.ComboBox()
        self.UploadsAllowed.show()
        self.UploadsAllowed_List.append([""])

        self.UploadsAllowed.set_model(self.UploadsAllowed_List)
        cell = gtk.CellRendererText()
        self.UploadsAllowed.pack_start(cell, True)
        self.UploadsAllowed.add_attribute(cell, 'text', 0)
        self.hbox211.pack_start(self.UploadsAllowed, False, True, 0)

        self.vbox114.pack_start(self.hbox211)

        self.expander5.add(self.vbox114)

        self.label362 = gtk.Label("")
        self.label362.set_markup(_("<b>Upload Queue:</b>"))
        self.label362.show()
        self.expander5.set_label_widget(self.label362)

        self.vbox81.pack_start(self.expander5, False, True, 0)

        self.expander6 = gtk.Expander()
        self.expander6.set_expanded(True)
        self.expander6.show()
        self.expander6.set_spacing(5)

        self.vbox117 = gtk.VBox(False, 0)
        self.vbox117.show()

        self.hbox176 = gtk.HBox(False, 0)
        self.hbox176.show()
        self.hbox176.set_spacing(5)

        self.FriendsOnly = gtk.CheckButton()
        self.tooltips.set_tip(self.FriendsOnly, _("If buddy shares are enabled, they will be shared. Otherwise normal shares will be used."))
        self.FriendsOnly.set_label(_("Share to friends only"))
        self.FriendsOnly.show()
        self.FriendsOnly.connect("toggled", self.OnFriendsOnlyToggled)
        self.hbox176.pack_start(self.FriendsOnly, False, False, 0)

        self.PreferFriends = gtk.CheckButton()
        self.tooltips.set_tip(self.PreferFriends, _("Friends will have higher priority in the queue, the same as globally privileged users"))
        self.PreferFriends.set_label(_("Privilege all my friends"))
        self.PreferFriends.show()
        self.hbox176.pack_start(self.PreferFriends, False, False, 0)

        self.vbox117.pack_start(self.hbox176)

        self.expander6.add(self.vbox117)

        self.label363 = gtk.Label("")
        self.label363.set_markup(_("<b>Privileges:</b>"))
        self.label363.show()
        self.expander6.set_label_widget(self.label363)

        self.vbox81.pack_start(self.expander6, False, True, 0)

        self.expander7 = gtk.Expander()
        self.expander7.show()

        self.vbox115 = gtk.VBox(False, 0)
        self.vbox115.show()

        self.hbox212 = gtk.HBox(False, 0)
        self.hbox212.show()
        self.hbox212.set_spacing(3)

        self.label364 = gtk.Label("")
        self.label364.set_alignment(0, 0.50)
        self.label364.set_markup(_("<b>Do not download these file types:</b>"))
        self.label364.show()
        self.hbox212.pack_start(self.label364, False, False, 0)

        self.DownloadFilter = gtk.CheckButton()
        self.DownloadFilter.set_label(_("Enable Filters"))
        self.DownloadFilter.show()
        self.DownloadFilter.connect("toggled", self.OnEnableFiltersToggle)
        self.hbox212.pack_start(self.DownloadFilter, False, False, 0)

        self.vbox115.pack_start(self.hbox212, False, True, 0)

        self.label365 = gtk.Label("")
        self.label365.set_alignment(0, 0.50)
        self.label365.set_line_wrap(True)
        self.label365.set_markup(_("<b>Syntax:</b> Letters are Case Insensitive, All Python Regular Expressions are supported if escaping is disabled. For simple filters, keep escaping enabled."))
        self.label365.show()
        self.vbox115.pack_start(self.label365, False, False, 0)

        self.table5 = gtk.Table()
        self.table5.show()
        self.table5.set_row_spacings(3)
        self.table5.set_col_spacings(3)

        self.vbox118 = gtk.VBox(False, 0)
        self.vbox118.show()
        self.vbox118.set_spacing(3)
        self.vbox118.set_border_width(3)

        self.VerifyFilters = gtk.Button()
        self.VerifyFilters.show()
        self.VerifyFilters.connect("clicked", self.OnVerifyFilter)

        self.alignment99 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment99.show()

        self.hbox219 = gtk.HBox(False, 0)
        self.hbox219.show()
        self.hbox219.set_spacing(2)

        self.image93 = gtk.Image()
        self.image93.set_from_stock(gtk.STOCK_SPELL_CHECK, 4)
        self.image93.show()
        self.hbox219.pack_start(self.image93, False, False, 0)

        self.label373 = gtk.Label(_("Verify Filters"))
        self.label373.show()
        self.hbox219.pack_start(self.label373, False, False, 0)

        self.alignment99.add(self.hbox219)

        self.VerifyFilters.add(self.alignment99)

        self.vbox118.pack_start(self.VerifyFilters, False, False, 0)

        self.table5.attach(self.vbox118, 1, 2, 0, 1, gtk.FILL, gtk.FILL, 0, 0)

        self.scrolledwindow16 = gtk.ScrolledWindow()
        self.scrolledwindow16.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolledwindow16.show()
        self.scrolledwindow16.set_shadow_type(gtk.SHADOW_IN)

        self.FilterView = gtk.TreeView()
        self.FilterView.show()
        self.scrolledwindow16.add(self.FilterView)

        self.table5.attach(self.scrolledwindow16, 0, 1, 1, 2, gtk.EXPAND|gtk.FILL, gtk.FILL, 0, 0)

        self.hbox218 = gtk.HBox(False, 0)
        self.hbox218.show()
        self.hbox218.set_spacing(5)

        self.VerifiedLabel = gtk.Label("")
        self.VerifiedLabel.set_alignment(1, 0.50)
        self.VerifiedLabel.set_line_wrap(True)
        self.VerifiedLabel.set_markup(_("<b>Unverified</b>"))
        self.VerifiedLabel.show()
        self.hbox218.pack_start(self.VerifiedLabel)

        self.table5.attach(self.hbox218, 0, 1, 0, 1, gtk.EXPAND|gtk.FILL, gtk.FILL, 0, 0)

        self.vbox116 = gtk.VBox(False, 0)
        self.vbox116.show()
        self.vbox116.set_spacing(3)
        self.vbox116.set_border_width(3)

        self.AddFilter = gtk.Button()
        self.AddFilter.show()
        self.AddFilter.connect("clicked", self.OnAddFilter)

        self.alignment95 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment95.show()

        self.hbox214 = gtk.HBox(False, 0)
        self.hbox214.show()
        self.hbox214.set_spacing(2)

        self.image89 = gtk.Image()
        self.image89.set_from_stock(gtk.STOCK_ADD, 4)
        self.image89.show()
        self.hbox214.pack_start(self.image89, False, False, 0)

        self.label366 = gtk.Label(_("Add..."))
        self.label366.show()
        self.hbox214.pack_start(self.label366, False, False, 0)

        self.alignment95.add(self.hbox214)

        self.AddFilter.add(self.alignment95)

        self.vbox116.pack_start(self.AddFilter, False, False, 0)

        self.EditFilter = gtk.Button()
        self.EditFilter.show()
        self.EditFilter.connect("clicked", self.OnEditFilter)

        self.alignment96 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment96.show()

        self.hbox215 = gtk.HBox(False, 0)
        self.hbox215.show()
        self.hbox215.set_spacing(2)

        self.image90 = gtk.Image()
        self.image90.set_from_stock(gtk.STOCK_EDIT, 4)
        self.image90.show()
        self.hbox215.pack_start(self.image90, False, False, 0)

        self.label367 = gtk.Label(_("Edit Filter"))
        self.label367.show()
        self.hbox215.pack_start(self.label367, False, False, 0)

        self.alignment96.add(self.hbox215)

        self.EditFilter.add(self.alignment96)

        self.vbox116.pack_start(self.EditFilter, False, False, 0)

        self.RemoveFilter = gtk.Button()
        self.RemoveFilter.show()
        self.RemoveFilter.connect("clicked", self.OnRemoveFilter)

        self.alignment97 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment97.show()

        self.hbox216 = gtk.HBox(False, 0)
        self.hbox216.show()
        self.hbox216.set_spacing(2)

        self.image91 = gtk.Image()
        self.image91.set_from_stock(gtk.STOCK_REMOVE, 4)
        self.image91.show()
        self.hbox216.pack_start(self.image91, False, False, 0)

        self.label368 = gtk.Label(_("Remove"))
        self.label368.show()
        self.hbox216.pack_start(self.label368, False, False, 0)

        self.alignment97.add(self.hbox216)

        self.RemoveFilter.add(self.alignment97)

        self.vbox116.pack_start(self.RemoveFilter, False, False, 0)

        self.DefaultFilters = gtk.Button()
        self.DefaultFilters.show()
        self.DefaultFilters.connect("clicked", self.OnDefaultFilters)

        self.alignment98 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment98.show()

        self.hbox217 = gtk.HBox(False, 0)
        self.hbox217.show()
        self.hbox217.set_spacing(2)

        self.image92 = gtk.Image()
        self.image92.set_from_stock(gtk.STOCK_REFRESH, 4)
        self.image92.show()
        self.hbox217.pack_start(self.image92, False, False, 0)

        self.label369 = gtk.Label(_("Load Defaults"))
        self.label369.show()
        self.hbox217.pack_start(self.label369, False, False, 0)

        self.alignment98.add(self.hbox217)

        self.DefaultFilters.add(self.alignment98)

        self.vbox116.pack_start(self.DefaultFilters, False, False, 0)

        self.table5.attach(self.vbox116, 1, 2, 1, 2, gtk.FILL, gtk.FILL, 0, 0)

        self.vbox115.pack_start(self.table5)

        self.expander7.add(self.vbox115)

        self.label372 = gtk.Label("")
        self.label372.set_markup(_("<b>Download Filters:</b>"))
        self.label372.show()
        self.expander7.set_label_widget(self.label372)

        self.vbox81.pack_start(self.expander7, False, True, 0)

        self.LockIncoming = gtk.CheckButton()
        self.LockIncoming.set_label(_("Lock incoming files (turn off for NFS)"))
        self.LockIncoming.show()
        self.vbox81.pack_start(self.LockIncoming, False, False, 0)

        self.Main.add(self.vbox81)

        self.label183 = gtk.Label(_("Transfers"))
        self.label183.show()
        self.Main.set_label_widget(self.label183)


        if create:
            self.TransfersFrame.add(self.Main)

    def OnQueueUseSlotsToggled(self, widget):
        pass

    def OnLimitToggled(self, widget):
        pass

    def OnFriendsOnlyToggled(self, widget):
        pass

    def OnEnableFiltersToggle(self, widget):
        pass

    def OnVerifyFilter(self, widget):
        pass

    def OnAddFilter(self, widget):
        pass

    def OnEditFilter(self, widget):
        pass

    def OnRemoveFilter(self, widget):
        pass

    def OnDefaultFilters(self, widget):
        pass

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class UserinfoFrame:
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
            self.UserinfoFrame = gtk.Window()
            self.UserinfoFrame.set_title(_("Userinfo"))
            self.UserinfoFrame.add_accel_group(self.accel_group)
            self.UserinfoFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()

        self.vbox84 = gtk.VBox(False, 0)
        self.vbox84.show()
        self.vbox84.set_spacing(10)
        self.vbox84.set_border_width(5)

        self.vbox85 = gtk.VBox(False, 0)
        self.vbox85.show()

        self.label193 = gtk.Label(_("Self description:"))
        self.label193.set_alignment(0, 0.50)
        self.label193.show()
        self.vbox85.pack_start(self.label193, False, False, 0)

        self.hbox121 = gtk.HBox(False, 0)
        self.hbox121.show()

        self.scrolledwindow9 = gtk.ScrolledWindow()
        self.scrolledwindow9.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolledwindow9.set_size_request(250, -1)
        self.scrolledwindow9.show()
        self.scrolledwindow9.set_shadow_type(gtk.SHADOW_IN)

        self.Description = gtk.TextView()
        self.Description.set_wrap_mode(gtk.WRAP_WORD)
        self.Description.show()
        self.scrolledwindow9.add(self.Description)

        self.hbox121.pack_start(self.scrolledwindow9)

        self.vbox85.pack_start(self.hbox121)

        self.vbox84.pack_start(self.vbox85)

        self.label265 = gtk.Label(_("Image:"))
        self.label265.set_alignment(0, 0.50)
        self.label265.show()
        self.vbox84.pack_start(self.label265, False, False, 0)

        self.hbox122 = gtk.HBox(False, 0)
        self.hbox122.show()
        self.hbox122.set_spacing(5)

        self.Image = gtk.Entry()
        self.Image.set_size_request(250, -1)
        self.Image.show()
        self.hbox122.pack_start(self.Image)

        self.button53 = gtk.Button()
        self.button53.show()
        self.button53.connect("clicked", self.OnChooseImage)

        self.alignment57 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment57.show()

        self.hbox151 = gtk.HBox(False, 0)
        self.hbox151.show()
        self.hbox151.set_spacing(2)

        self.image54 = gtk.Image()
        self.image54.set_from_stock(gtk.STOCK_OPEN, 4)
        self.image54.show()
        self.hbox151.pack_start(self.image54, False, False, 0)

        self.label230 = gtk.Label(_("Choose..."))
        self.label230.show()
        self.hbox151.pack_start(self.label230, False, False, 0)

        self.alignment57.add(self.hbox151)

        self.button53.add(self.alignment57)

        self.hbox122.pack_start(self.button53, False, False, 0)

        self.vbox84.pack_start(self.hbox122, False, False, 0)

        self.Main.add(self.vbox84)

        self.label192 = gtk.Label(_("Personal settings"))
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
            self.BloatFrame = gtk.Window()
            self.BloatFrame.set_title(_("Bloat"))
            self.BloatFrame.add_accel_group(self.accel_group)
            self.BloatFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()

        self.vboxUI = gtk.VBox(False, 0)
        self.vboxUI.show()
        self.vboxUI.set_spacing(5)
        self.vboxUI.set_border_width(5)

        self.SpellCheck = gtk.CheckButton()
        self.tooltips.set_tip(self.SpellCheck, _("Libsexy Website: http://www.chipx86.com/wiki/Libsexy \nlibsexy and sexy-python bindings required."))
        self.SpellCheck.set_label(_("Enable spell checker (requires a restart)"))
        self.SpellCheck.show()
        self.vboxUI.pack_start(self.SpellCheck, False, False, 0)

        self.ExitDialog = gtk.CheckButton()
        self.ExitDialog.set_label(_("Show confirmation dialog when closing the main window"))
        self.ExitDialog.show()
        self.vboxUI.pack_start(self.ExitDialog, False, False, 0)

        self.ShowTransferButtons = gtk.CheckButton()
        self.ShowTransferButtons.set_label(_("Show Buttons in Transfers Tabs"))
        self.ShowTransferButtons.show()
        self.vboxUI.pack_start(self.ShowTransferButtons, False, False, 0)

        self.hbox177 = gtk.HBox(False, 0)
        self.hbox177.show()
        self.hbox177.set_spacing(10)

        self.ReopenPrivateChats = gtk.CheckButton()
        self.ReopenPrivateChats.set_label(_("Reopen last Private Chat messages"))
        self.ReopenPrivateChats.show()
        self.hbox177.pack_start(self.ReopenPrivateChats, False, False, 0)

        self.vboxUI.pack_start(self.hbox177, False, False, 0)

        self.hbox172 = gtk.HBox(False, 0)
        self.hbox172.show()

        self.chatfontlabel = gtk.Label(_("Chat Font:"))
        self.chatfontlabel.set_alignment(0, 0.50)
        self.chatfontlabel.show()
        self.hbox172.pack_start(self.chatfontlabel, False, False, 0)

        self.SelectChatFont = gtk.FontButton()
        self.SelectChatFont.show()
        self.hbox172.pack_start(self.SelectChatFont, False, False, 5)

        self.vboxUI.pack_start(self.hbox172, False, True, 0)

        self.hbox182 = gtk.HBox(False, 0)
        self.hbox182.show()
        self.hbox182.set_spacing(5)

        self.label213 = gtk.Label(_("Decimal seperator:"))
        self.label213.set_alignment(0, 0.50)
        self.label213.show()
        self.hbox182.pack_start(self.label213, False, False, 0)

        self.DecimalSep_List = gtk.ListStore(gobject.TYPE_STRING)
        self.DecimalSep = gtk.ComboBoxEntry()
        self.DecimalSep.set_size_request(99, -1)
        self.DecimalSep.show()

        self.comboboxentry_entry3 = self.DecimalSep.child

        self.DecimalSep.set_model(self.DecimalSep_List)
        self.DecimalSep.set_text_column(0)
        self.hbox182.pack_start(self.DecimalSep, False, False, 0)

        self.vboxUI.pack_start(self.hbox182, False, False, 0)

        self.expander2 = gtk.Expander()
        self.expander2.show()

        self.table2 = gtk.Table()
        self.table2.show()
        self.table2.set_row_spacings(3)
        self.table2.set_col_spacings(15)

        self.DefaultInput = gtk.Button()
        self.DefaultInput.show()

        self.alignment101 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment101.show()

        self.hbox221 = gtk.HBox(False, 0)
        self.hbox221.show()
        self.hbox221.set_spacing(2)

        self.image95 = gtk.Image()
        self.image95.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image95.show()
        self.hbox221.pack_start(self.image95, False, False, 0)

        self.label375 = gtk.Label(_("Default"))
        self.label375.show()
        self.hbox221.pack_start(self.label375, False, False, 0)

        self.alignment101.add(self.hbox221)

        self.DefaultInput.add(self.alignment101)

        self.table2.attach(self.DefaultInput, 2, 3, 13, 14, gtk.FILL, 0, 0, 0)

        self.InputColor = gtk.Entry()
        self.InputColor.set_editable(False)
        self.InputColor.show()
        self.table2.attach(self.InputColor, 1, 2, 13, 14, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.PickInput = gtk.Button()
        self.PickInput.show()

        self.alignment100 = gtk.Alignment(0, 0.5, 0, 0)
        self.alignment100.show()

        self.hbox220 = gtk.HBox(False, 0)
        self.hbox220.show()
        self.hbox220.set_spacing(2)

        self.image94 = gtk.Image()
        self.image94.set_from_stock(gtk.STOCK_SELECT_COLOR, 4)
        self.image94.show()
        self.hbox220.pack_start(self.image94, False, False, 0)

        self.label374 = gtk.Label(_("Input Text"))
        self.label374.show()
        self.hbox220.pack_start(self.label374, False, False, 0)

        self.alignment100.add(self.hbox220)

        self.PickInput.add(self.alignment100)

        self.table2.attach(self.PickInput, 0, 1, 13, 14, gtk.FILL, 0, 0, 0)

        self.hbox197 = gtk.HBox(False, 0)
        self.hbox197.show()
        self.hbox197.set_spacing(3)

        self.label321 = gtk.Label(_("Username Font Style:"))
        self.label321.show()
        self.hbox197.pack_start(self.label321, False, False, 0)

        self.UsernameStyle_List = gtk.ListStore(gobject.TYPE_STRING)
        self.UsernameStyle = gtk.ComboBoxEntry()
        self.UsernameStyle.show()

        self.comboboxentry_entry4 = self.UsernameStyle.child

        self.UsernameStyle.set_model(self.UsernameStyle_List)
        self.UsernameStyle.set_text_column(0)
        self.hbox197.pack_start(self.UsernameStyle, False, True, 0)

        self.table2.attach(self.hbox197, 0, 3, 11, 12, gtk.FILL, gtk.EXPAND|gtk.FILL, 0, 0)

        self.PickBackground = gtk.Button()
        self.PickBackground.show()

        self.alignment93 = gtk.Alignment(0, 0.5, 0, 0)
        self.alignment93.show()

        self.hbox209 = gtk.HBox(False, 0)
        self.hbox209.show()
        self.hbox209.set_spacing(2)

        self.image87 = gtk.Image()
        self.image87.set_from_stock(gtk.STOCK_SELECT_COLOR, 4)
        self.image87.show()
        self.hbox209.pack_start(self.image87, False, False, 0)

        self.label359 = gtk.Label(_("Background"))
        self.label359.show()
        self.hbox209.pack_start(self.label359, False, False, 0)

        self.alignment93.add(self.hbox209)

        self.PickBackground.add(self.alignment93)

        self.table2.attach(self.PickBackground, 0, 1, 12, 13, gtk.FILL, 0, 0, 0)

        self.BackgroundColor = gtk.Entry()
        self.BackgroundColor.set_editable(False)
        self.BackgroundColor.show()
        self.table2.attach(self.BackgroundColor, 1, 2, 12, 13, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.DefaultBackground = gtk.Button()
        self.DefaultBackground.show()

        self.alignment94 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment94.show()

        self.hbox210 = gtk.HBox(False, 0)
        self.hbox210.show()
        self.hbox210.set_spacing(2)

        self.image88 = gtk.Image()
        self.image88.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image88.show()
        self.hbox210.pack_start(self.image88, False, False, 0)

        self.label360 = gtk.Label(_("Default"))
        self.label360.show()
        self.hbox210.pack_start(self.label360, False, False, 0)

        self.alignment94.add(self.hbox210)

        self.DefaultBackground.add(self.alignment94)

        self.table2.attach(self.DefaultBackground, 2, 3, 12, 13, gtk.FILL, 0, 0, 0)

        self.PickOffline = gtk.Button()
        self.PickOffline.show()

        self.alignment79 = gtk.Alignment(0, 0.5, 0, 0)
        self.alignment79.show()

        self.hbox184 = gtk.HBox(False, 0)
        self.hbox184.show()
        self.hbox184.set_spacing(2)

        self.image73 = gtk.Image()
        self.image73.set_from_stock(gtk.STOCK_SELECT_COLOR, 4)
        self.image73.show()
        self.hbox184.pack_start(self.image73, False, False, 0)

        self.label309 = gtk.Label(_("Offline"))
        self.label309.show()
        self.hbox184.pack_start(self.label309, False, False, 0)

        self.alignment79.add(self.hbox184)

        self.PickOffline.add(self.alignment79)

        self.table2.attach(self.PickOffline, 0, 1, 9, 10, gtk.FILL, 0, 0, 0)

        self.PickOnline = gtk.Button()
        self.PickOnline.show()

        self.alignment78 = gtk.Alignment(0, 0.5, 0, 0)
        self.alignment78.show()

        self.hbox183 = gtk.HBox(False, 0)
        self.hbox183.show()
        self.hbox183.set_spacing(2)

        self.image72 = gtk.Image()
        self.image72.set_from_stock(gtk.STOCK_SELECT_COLOR, 4)
        self.image72.show()
        self.hbox183.pack_start(self.image72, False, False, 0)

        self.label308 = gtk.Label(_("Online"))
        self.label308.show()
        self.hbox183.pack_start(self.label308, False, False, 0)

        self.alignment78.add(self.hbox183)

        self.PickOnline.add(self.alignment78)

        self.table2.attach(self.PickOnline, 0, 1, 8, 9, gtk.FILL, 0, 0, 0)

        self.DefaultAway = gtk.Button()
        self.DefaultAway.show()

        self.alignment83 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment83.show()

        self.hbox188 = gtk.HBox(False, 0)
        self.hbox188.show()
        self.hbox188.set_spacing(2)

        self.image77 = gtk.Image()
        self.image77.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image77.show()
        self.hbox188.pack_start(self.image77, False, False, 0)

        self.label313 = gtk.Label(_("Default"))
        self.label313.show()
        self.hbox188.pack_start(self.label313, False, False, 0)

        self.alignment83.add(self.hbox188)

        self.DefaultAway.add(self.alignment83)

        self.table2.attach(self.DefaultAway, 2, 3, 10, 11, gtk.FILL, 0, 0, 0)

        self.PickAway = gtk.Button()
        self.PickAway.show()

        self.alignment80 = gtk.Alignment(0, 0.5, 0, 0)
        self.alignment80.show()

        self.hbox185 = gtk.HBox(False, 0)
        self.hbox185.show()
        self.hbox185.set_spacing(2)

        self.image74 = gtk.Image()
        self.image74.set_from_stock(gtk.STOCK_SELECT_COLOR, 4)
        self.image74.show()
        self.hbox185.pack_start(self.image74, False, False, 0)

        self.label310 = gtk.Label(_("Away"))
        self.label310.show()
        self.hbox185.pack_start(self.label310, False, False, 0)

        self.alignment80.add(self.hbox185)

        self.PickAway.add(self.alignment80)

        self.table2.attach(self.PickAway, 0, 1, 10, 11, gtk.FILL, 0, 0, 0)

        self.AwayColor = gtk.Entry()
        self.AwayColor.set_editable(False)
        self.AwayColor.show()
        self.table2.attach(self.AwayColor, 1, 2, 10, 11, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.UsernameHotspots = gtk.CheckButton()
        self.UsernameHotspots.set_label(_("Username Colours and Hotspots"))
        self.UsernameHotspots.show()
        self.UsernameHotspots.connect("toggled", self.OnUsernameHotspotsToggled)
        self.table2.attach(self.UsernameHotspots, 0, 3, 7, 8, gtk.FILL, 0, 0, 0)

        self.DefaultOffline = gtk.Button()
        self.DefaultOffline.show()

        self.alignment82 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment82.show()

        self.hbox187 = gtk.HBox(False, 0)
        self.hbox187.show()
        self.hbox187.set_spacing(2)

        self.image76 = gtk.Image()
        self.image76.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image76.show()
        self.hbox187.pack_start(self.image76, False, False, 0)

        self.label312 = gtk.Label(_("Default"))
        self.label312.show()
        self.hbox187.pack_start(self.label312, False, False, 0)

        self.alignment82.add(self.hbox187)

        self.DefaultOffline.add(self.alignment82)

        self.table2.attach(self.DefaultOffline, 2, 3, 9, 10, gtk.FILL, 0, 0, 0)

        self.DefaultOnline = gtk.Button()
        self.DefaultOnline.show()

        self.alignment81 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment81.show()

        self.hbox186 = gtk.HBox(False, 0)
        self.hbox186.show()
        self.hbox186.set_spacing(2)

        self.image75 = gtk.Image()
        self.image75.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image75.show()
        self.hbox186.pack_start(self.image75, False, False, 0)

        self.label311 = gtk.Label(_("Default"))
        self.label311.show()
        self.hbox186.pack_start(self.label311, False, False, 0)

        self.alignment81.add(self.hbox186)

        self.DefaultOnline.add(self.alignment81)

        self.table2.attach(self.DefaultOnline, 2, 3, 8, 9, gtk.FILL, 0, 0, 0)

        self.OfflineColor = gtk.Entry()
        self.OfflineColor.set_editable(False)
        self.OfflineColor.show()
        self.table2.attach(self.OfflineColor, 1, 2, 9, 10, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.OnlineColor = gtk.Entry()
        self.OnlineColor.set_editable(False)
        self.OnlineColor.show()
        self.table2.attach(self.OnlineColor, 1, 2, 8, 9, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.PickQueue = gtk.Button()
        self.PickQueue.show()

        self.alignment47 = gtk.Alignment(0, 0.5, 0, 0)
        self.alignment47.show()

        self.hbox136 = gtk.HBox(False, 0)
        self.hbox136.show()
        self.hbox136.set_spacing(2)

        self.image44 = gtk.Image()
        self.image44.set_from_stock(gtk.STOCK_SELECT_COLOR, 4)
        self.image44.show()
        self.hbox136.pack_start(self.image44, False, False, 0)

        self.label210 = gtk.Label(_("With queue"))
        self.label210.show()
        self.hbox136.pack_start(self.label210, False, False, 0)

        self.alignment47.add(self.hbox136)

        self.PickQueue.add(self.alignment47)

        self.table2.attach(self.PickQueue, 0, 1, 6, 7, gtk.FILL, 0, 0, 0)

        self.Queue = gtk.Entry()
        self.Queue.set_editable(False)
        self.Queue.show()
        self.table2.attach(self.Queue, 1, 2, 6, 7, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.DefaultQueue = gtk.Button()
        self.DefaultQueue.show()

        self.alignment49 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment49.show()

        self.hbox138 = gtk.HBox(False, 0)
        self.hbox138.show()
        self.hbox138.set_spacing(2)

        self.image46 = gtk.Image()
        self.image46.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image46.show()
        self.hbox138.pack_start(self.image46, False, False, 0)

        self.label212 = gtk.Label(_("Default"))
        self.label212.show()
        self.hbox138.pack_start(self.label212, False, False, 0)

        self.alignment49.add(self.hbox138)

        self.DefaultQueue.add(self.alignment49)

        self.table2.attach(self.DefaultQueue, 2, 3, 6, 7, gtk.FILL, 0, 0, 0)

        self.DefaultImmediate = gtk.Button()
        self.DefaultImmediate.show()

        self.alignment48 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment48.show()

        self.hbox137 = gtk.HBox(False, 0)
        self.hbox137.show()
        self.hbox137.set_spacing(2)

        self.image45 = gtk.Image()
        self.image45.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image45.show()
        self.hbox137.pack_start(self.image45, False, False, 0)

        self.label211 = gtk.Label(_("Default"))
        self.label211.show()
        self.hbox137.pack_start(self.label211, False, False, 0)

        self.alignment48.add(self.hbox137)

        self.DefaultImmediate.add(self.alignment48)

        self.table2.attach(self.DefaultImmediate, 2, 3, 5, 6, gtk.FILL, 0, 0, 0)

        self.Immediate = gtk.Entry()
        self.Immediate.set_editable(False)
        self.Immediate.show()
        self.table2.attach(self.Immediate, 1, 2, 5, 6, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.PickImmediate = gtk.Button()
        self.PickImmediate.show()

        self.alignment46 = gtk.Alignment(0, 0.5, 0, 0)
        self.alignment46.show()

        self.hbox135 = gtk.HBox(False, 0)
        self.hbox135.show()
        self.hbox135.set_spacing(2)

        self.image43 = gtk.Image()
        self.image43.set_from_stock(gtk.STOCK_SELECT_COLOR, 4)
        self.image43.show()
        self.hbox135.pack_start(self.image43, False, False, 0)

        self.label209 = gtk.Label(_("List Text"))
        self.label209.show()
        self.hbox135.pack_start(self.label209, False, False, 0)

        self.alignment46.add(self.hbox135)

        self.PickImmediate.add(self.alignment46)

        self.table2.attach(self.PickImmediate, 0, 1, 5, 6, gtk.FILL, 0, 0, 0)

        self.label208 = gtk.Label("")
        self.label208.set_alignment(0, 0.50)
        self.label208.set_padding(0, 5)
        self.label208.set_markup(_("<b>List and search colours</b>"))
        self.label208.show()
        self.table2.attach(self.label208, 0, 3, 4, 5, gtk.FILL, 0, 0, 0)

        self.DefaultHighlight = gtk.Button()
        self.DefaultHighlight.show()

        self.alignment42 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment42.show()

        self.hbox131 = gtk.HBox(False, 0)
        self.hbox131.show()
        self.hbox131.set_spacing(2)

        self.image39 = gtk.Image()
        self.image39.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image39.show()
        self.hbox131.pack_start(self.image39, False, False, 0)

        self.label204 = gtk.Label(_("Default"))
        self.label204.show()
        self.hbox131.pack_start(self.label204, False, False, 0)

        self.alignment42.add(self.hbox131)

        self.DefaultHighlight.add(self.alignment42)

        self.table2.attach(self.DefaultHighlight, 2, 3, 3, 4, gtk.FILL, 0, 0, 0)

        self.DefaultMe = gtk.Button()
        self.DefaultMe.show()

        self.alignment41 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment41.show()

        self.hbox130 = gtk.HBox(False, 0)
        self.hbox130.show()
        self.hbox130.set_spacing(2)

        self.image38 = gtk.Image()
        self.image38.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image38.show()
        self.hbox130.pack_start(self.image38, False, False, 0)

        self.label203 = gtk.Label(_("Default"))
        self.label203.show()
        self.hbox130.pack_start(self.label203, False, False, 0)

        self.alignment41.add(self.hbox130)

        self.DefaultMe.add(self.alignment41)

        self.table2.attach(self.DefaultMe, 2, 3, 2, 3, gtk.FILL, 0, 0, 0)

        self.DefaultLocal = gtk.Button()
        self.DefaultLocal.show()

        self.alignment40 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment40.show()

        self.hbox129 = gtk.HBox(False, 0)
        self.hbox129.show()
        self.hbox129.set_spacing(2)

        self.image37 = gtk.Image()
        self.image37.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image37.show()
        self.hbox129.pack_start(self.image37, False, False, 0)

        self.label202 = gtk.Label(_("Default"))
        self.label202.show()
        self.hbox129.pack_start(self.label202, False, False, 0)

        self.alignment40.add(self.hbox129)

        self.DefaultLocal.add(self.alignment40)

        self.table2.attach(self.DefaultLocal, 2, 3, 1, 2, gtk.FILL, 0, 0, 0)

        self.DefaultRemote = gtk.Button()
        self.DefaultRemote.show()

        self.alignment36 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment36.show()

        self.hbox125 = gtk.HBox(False, 0)
        self.hbox125.show()
        self.hbox125.set_spacing(2)

        self.image33 = gtk.Image()
        self.image33.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image33.show()
        self.hbox125.pack_start(self.image33, False, False, 0)

        self.label198 = gtk.Label(_("Default"))
        self.label198.show()
        self.hbox125.pack_start(self.label198, False, False, 0)

        self.alignment36.add(self.hbox125)

        self.DefaultRemote.add(self.alignment36)

        self.table2.attach(self.DefaultRemote, 2, 3, 0, 1, gtk.FILL, 0, 0, 0)

        self.Highlight = gtk.Entry()
        self.Highlight.set_editable(False)
        self.Highlight.show()
        self.table2.attach(self.Highlight, 1, 2, 3, 4, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.Me = gtk.Entry()
        self.Me.set_editable(False)
        self.Me.show()
        self.table2.attach(self.Me, 1, 2, 2, 3, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.Local = gtk.Entry()
        self.Local.set_editable(False)
        self.Local.show()
        self.table2.attach(self.Local, 1, 2, 1, 2, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.Remote = gtk.Entry()
        self.Remote.set_editable(False)
        self.Remote.show()
        self.table2.attach(self.Remote, 1, 2, 0, 1, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.PickHighlight = gtk.Button()
        self.PickHighlight.show()

        self.alignment45 = gtk.Alignment(0, 0.5, 0, 0)
        self.alignment45.show()

        self.hbox134 = gtk.HBox(False, 0)
        self.hbox134.show()
        self.hbox134.set_spacing(2)

        self.image42 = gtk.Image()
        self.image42.set_from_stock(gtk.STOCK_SELECT_COLOR, 4)
        self.image42.show()
        self.hbox134.pack_start(self.image42, False, False, 0)

        self.label207 = gtk.Label(_("Highlight text"))
        self.label207.show()
        self.hbox134.pack_start(self.label207, False, False, 0)

        self.alignment45.add(self.hbox134)

        self.PickHighlight.add(self.alignment45)

        self.table2.attach(self.PickHighlight, 0, 1, 3, 4, gtk.FILL, 0, 0, 0)

        self.PickMe = gtk.Button()
        self.PickMe.show()

        self.alignment44 = gtk.Alignment(0, 0.5, 0, 0)
        self.alignment44.show()

        self.hbox133 = gtk.HBox(False, 0)
        self.hbox133.show()
        self.hbox133.set_spacing(2)

        self.image41 = gtk.Image()
        self.image41.set_from_stock(gtk.STOCK_SELECT_COLOR, 4)
        self.image41.show()
        self.hbox133.pack_start(self.image41, False, False, 0)

        self.label206 = gtk.Label(_("/me text"))
        self.label206.show()
        self.hbox133.pack_start(self.label206, False, False, 0)

        self.alignment44.add(self.hbox133)

        self.PickMe.add(self.alignment44)

        self.table2.attach(self.PickMe, 0, 1, 2, 3, gtk.FILL, 0, 0, 0)

        self.PickLocal = gtk.Button()
        self.PickLocal.show()

        self.alignment43 = gtk.Alignment(0, 0.5, 0, 0)
        self.alignment43.show()

        self.hbox132 = gtk.HBox(False, 0)
        self.hbox132.show()
        self.hbox132.set_spacing(2)

        self.image40 = gtk.Image()
        self.image40.set_from_stock(gtk.STOCK_SELECT_COLOR, 4)
        self.image40.show()
        self.hbox132.pack_start(self.image40, False, False, 0)

        self.label205 = gtk.Label(_("Local text"))
        self.label205.show()
        self.hbox132.pack_start(self.label205, False, False, 0)

        self.alignment43.add(self.hbox132)

        self.PickLocal.add(self.alignment43)

        self.table2.attach(self.PickLocal, 0, 1, 1, 2, gtk.FILL, 0, 0, 0)

        self.PickRemote = gtk.Button()
        self.PickRemote.show()

        self.alignment35 = gtk.Alignment(0, 0.5, 0, 0)
        self.alignment35.show()

        self.hbox124 = gtk.HBox(False, 0)
        self.hbox124.show()
        self.hbox124.set_spacing(2)

        self.image32 = gtk.Image()
        self.image32.set_from_stock(gtk.STOCK_SELECT_COLOR, 4)
        self.image32.show()
        self.hbox124.pack_start(self.image32, False, False, 0)

        self.label197 = gtk.Label(_("Remote text"))
        self.label197.show()
        self.hbox124.pack_start(self.label197, False, False, 0)

        self.alignment35.add(self.hbox124)

        self.PickRemote.add(self.alignment35)

        self.table2.attach(self.PickRemote, 0, 1, 0, 1, gtk.FILL, 0, 0, 0)

        self.expander2.add(self.table2)

        self.label306 = gtk.Label("")
        self.label306.set_markup(_("<b>Colours</b>"))
        self.label306.show()
        self.expander2.set_label_widget(self.label306)

        self.vboxUI.pack_start(self.expander2, False, False, 0)

        self.expander3 = gtk.Expander()
        self.expander3.show()

        self.vbox106 = gtk.VBox(False, 0)
        self.vbox106.show()
        self.vbox106.set_spacing(3)
        self.vbox106.set_border_width(3)

        self.label343 = gtk.Label("")
        self.label343.set_alignment(0, 0.50)
        self.label343.set_line_wrap(True)
        self.label343.set_markup(_("<b>Warning:</b> This feature is resource intensive and may be very slow. If Nicotine<b>+</b> is started with this feature disabled, you will need to enable it and restart to see its effects."))
        self.label343.show()
        self.vbox106.pack_start(self.label343, False, False, 0)

        self.EnableTransparent = gtk.CheckButton()
        self.EnableTransparent.set_label(_("Enable Transparent Textviews"))
        self.EnableTransparent.show()
        self.EnableTransparent.set_border_width(3)
        self.EnableTransparent.connect("toggled", self.OnEnableTransparentToggled)
        self.vbox106.pack_start(self.EnableTransparent, False, False, 0)

        self.hbox198 = gtk.HBox(False, 0)
        self.hbox198.show()
        self.hbox198.set_spacing(5)

        self.PickTint = gtk.Button()
        self.PickTint.show()
        self.PickTint.connect("clicked", self.OnPickTint)

        self.alignment89 = gtk.Alignment(0, 0.5, 0, 0)
        self.alignment89.show()

        self.hbox199 = gtk.HBox(False, 0)
        self.hbox199.show()
        self.hbox199.set_spacing(2)
        self.hbox199.set_border_width(3)

        self.image83 = gtk.Image()
        self.image83.set_from_stock(gtk.STOCK_SELECT_COLOR, 4)
        self.image83.show()
        self.hbox199.pack_start(self.image83, False, False, 0)

        self.label344 = gtk.Label(_("Tint Color"))
        self.label344.show()
        self.hbox199.pack_start(self.label344, False, False, 0)

        self.alignment89.add(self.hbox199)

        self.PickTint.add(self.alignment89)

        self.hbox198.pack_start(self.PickTint, False, False, 0)

        self.TintColor = gtk.Entry()
        self.TintColor.set_editable(False)
        self.TintColor.show()
        self.hbox198.pack_start(self.TintColor, False, True, 0)

        self.DefaultTint = gtk.Button()
        self.DefaultTint.show()
        self.DefaultTint.connect("clicked", self.OnDefaultTint)

        self.alignment90 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment90.show()

        self.hbox200 = gtk.HBox(False, 0)
        self.hbox200.show()
        self.hbox200.set_spacing(2)

        self.image84 = gtk.Image()
        self.image84.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image84.show()
        self.hbox200.pack_start(self.image84, False, False, 0)

        self.label345 = gtk.Label(_("Default"))
        self.label345.show()
        self.hbox200.pack_start(self.label345, False, False, 0)

        self.alignment90.add(self.hbox200)

        self.DefaultTint.add(self.alignment90)

        self.hbox198.pack_start(self.DefaultTint, False, False, 0)

        self.vbox106.pack_start(self.hbox198, False, False, 0)

        self.hbox202 = gtk.HBox(False, 0)
        self.hbox202.show()

        self.vbox108 = gtk.VBox(False, 0)
        self.vbox108.show()

        self.label346 = gtk.Label(_("Red"))
        self.label346.show()
        self.vbox108.pack_start(self.label346)

        self.Red = gtk.HScale(gtk.Adjustment(value=0, lower=0, upper=255, step_incr=1, page_incr=20, page_size=0))
        self.Red.show()
        self.Red.set_digits(0)
        self.Red.connect("value_changed", self.ScaleColour)

        self.vbox108.pack_start(self.Red)

        self.hbox202.pack_start(self.vbox108)

        self.vbox109 = gtk.VBox(False, 0)
        self.vbox109.show()

        self.label348 = gtk.Label(_("Green"))
        self.label348.show()
        self.vbox109.pack_start(self.label348)

        self.Green = gtk.HScale(gtk.Adjustment(value=0, lower=0, upper=255, step_incr=1, page_incr=20, page_size=0))
        self.Green.show()
        self.Green.set_digits(0)
        self.Green.connect("value_changed", self.ScaleColour)

        self.vbox109.pack_start(self.Green)

        self.hbox202.pack_start(self.vbox109)

        self.vbox110 = gtk.VBox(False, 0)
        self.vbox110.show()

        self.label349 = gtk.Label("")
        self.label349.set_markup(_("Blue"))
        self.label349.show()
        self.vbox110.pack_start(self.label349)

        self.Blue = gtk.HScale(gtk.Adjustment(value=0, lower=0, upper=255, step_incr=1, page_incr=20, page_size=0))
        self.Blue.show()
        self.Blue.set_digits(0)
        self.Blue.connect("value_changed", self.ScaleColour)

        self.vbox110.pack_start(self.Blue)

        self.hbox202.pack_start(self.vbox110)

        self.vbox111 = gtk.VBox(False, 0)
        self.vbox111.show()

        self.label347 = gtk.Label(_("Alpha"))
        self.label347.show()
        self.vbox111.pack_start(self.label347)

        self.TintAlpha = gtk.HScale(gtk.Adjustment(value=0, lower=0, upper=255, step_incr=1, page_incr=20, page_size=0))
        self.TintAlpha.show()
        self.TintAlpha.set_digits(0)
        self.TintAlpha.connect("value_changed", self.ScaleColour)

        self.vbox111.pack_start(self.TintAlpha)

        self.hbox202.pack_start(self.vbox111)

        self.vbox106.pack_start(self.hbox202)

        self.expander3.add(self.vbox106)

        self.label342 = gtk.Label("")
        self.label342.set_markup(_("<b>Transparent Log Windows</b>"))
        self.label342.show()
        self.expander3.set_label_widget(self.label342)

        self.vboxUI.pack_start(self.expander3, False, False, 0)

        self.Main.add(self.vboxUI)

        self.label195 = gtk.Label(_("Extra stuff for your comfort"))
        self.label195.show()
        self.Main.set_label_widget(self.label195)


        if create:
            self.BloatFrame.add(self.Main)

    def OnUsernameHotspotsToggled(self, widget):
        pass

    def OnEnableTransparentToggled(self, widget):
        pass

    def OnPickTint(self, widget):
        pass

    def OnDefaultTint(self, widget):
        pass

    def ScaleColour(self, widget):
        pass

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class LogFrame:
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
            self.LogFrame = gtk.Window()
            self.LogFrame.set_title(_("Log"))
            self.LogFrame.add_accel_group(self.accel_group)
            self.LogFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()

        self.vbox89 = gtk.VBox(False, 0)
        self.vbox89.show()
        self.vbox89.set_spacing(10)
        self.vbox89.set_border_width(5)

        self.LogPrivate = gtk.CheckButton()
        self.LogPrivate.set_label(_("Log private chat by default"))
        self.LogPrivate.show()
        self.vbox89.pack_start(self.LogPrivate, False, False, 0)

        self.LogRooms = gtk.CheckButton()
        self.LogRooms.set_label(_("Log chatrooms by default"))
        self.LogRooms.show()
        self.vbox89.pack_start(self.LogRooms, False, False, 0)

        self.LogTransfers = gtk.CheckButton()
        self.LogTransfers.set_label(_("Log transfers"))
        self.LogTransfers.show()
        self.vbox89.pack_start(self.LogTransfers, False, False, 0)

        self.vbox90 = gtk.VBox(False, 0)
        self.vbox90.show()

        self.label217 = gtk.Label(_("Logs directory:"))
        self.label217.set_alignment(0, 0.50)
        self.label217.show()
        self.vbox90.pack_start(self.label217, False, False, 0)

        self.hbox140 = gtk.HBox(False, 0)
        self.hbox140.show()
        self.hbox140.set_spacing(5)

        self.LogDir = gtk.Entry()
        self.LogDir.set_text(_("~/"))
        self.LogDir.show()
        self.hbox140.pack_start(self.LogDir)

        self.button66 = gtk.Button()
        self.button66.show()
        self.button66.connect("clicked", self.OnChooseLogDir)

        self.alignment54 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment54.show()

        self.hbox148 = gtk.HBox(False, 0)
        self.hbox148.show()
        self.hbox148.set_spacing(2)

        self.image51 = gtk.Image()
        self.image51.set_from_stock(gtk.STOCK_OPEN, 4)
        self.image51.show()
        self.hbox148.pack_start(self.image51, False, False, 0)

        self.label227 = gtk.Label(_("Choose..."))
        self.label227.show()
        self.hbox148.pack_start(self.label227, False, False, 0)

        self.alignment54.add(self.hbox148)

        self.button66.add(self.alignment54)

        self.hbox140.pack_start(self.button66, False, False, 0)

        self.vbox90.pack_start(self.hbox140, False, False, 0)

        self.vbox89.pack_start(self.vbox90, False, False, 0)

        self.Main.add(self.vbox89)

        self.label216 = gtk.Label(_("Logging"))
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
            self.BanFrame = gtk.Window()
            self.BanFrame.set_title(_("Ban"))
            self.BanFrame.add_accel_group(self.accel_group)
            self.BanFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()

        self.vbox91 = gtk.VBox(False, 0)
        self.vbox91.show()
        self.vbox91.set_spacing(10)
        self.vbox91.set_border_width(5)

        self.hbox141 = gtk.HBox(False, 0)
        self.hbox141.show()
        self.hbox141.set_spacing(10)

        self.vbox92 = gtk.VBox(False, 0)
        self.vbox92.set_size_request(150, -1)
        self.vbox92.show()

        self.label219 = gtk.Label(_("Banned Users:"))
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

        self.vbox92.pack_start(self.scrolledwindow10)

        self.button80 = gtk.Button()
        self.button80.show()
        self.button80.connect("clicked", self.OnAddBanned)

        self.alignment62 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment62.show()

        self.hbox156 = gtk.HBox(False, 0)
        self.hbox156.show()
        self.hbox156.set_spacing(2)

        self.image59 = gtk.Image()
        self.image59.set_from_stock(gtk.STOCK_ADD, 4)
        self.image59.show()
        self.hbox156.pack_start(self.image59, False, False, 0)

        self.label238 = gtk.Label(_("Add..."))
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

        self.hbox157 = gtk.HBox(False, 0)
        self.hbox157.show()
        self.hbox157.set_spacing(2)

        self.image60 = gtk.Image()
        self.image60.set_from_stock(gtk.STOCK_REMOVE, 4)
        self.image60.show()
        self.hbox157.pack_start(self.image60, False, False, 0)

        self.label239 = gtk.Label(_("Remove"))
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

        self.hbox158 = gtk.HBox(False, 0)
        self.hbox158.show()
        self.hbox158.set_spacing(2)

        self.image61 = gtk.Image()
        self.image61.set_from_stock(gtk.STOCK_CLEAR, 4)
        self.image61.show()
        self.hbox158.pack_start(self.image61, False, False, 0)

        self.label240 = gtk.Label(_("Clear"))
        self.label240.show()
        self.hbox158.pack_start(self.label240, False, False, 0)

        self.alignment64.add(self.hbox158)

        self.button82.add(self.alignment64)

        self.vbox92.pack_start(self.button82, False, False, 0)

        self.hbox141.pack_start(self.vbox92)

        self.vbox97 = gtk.VBox(False, 0)
        self.vbox97.set_size_request(150, -1)
        self.vbox97.show()

        self.label237 = gtk.Label(_("Ignored users:"))
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

        self.vbox97.pack_start(self.scrolledwindow13)

        self.button77 = gtk.Button()
        self.button77.show()
        self.button77.connect("clicked", self.OnAddIgnored)

        self.alignment65 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment65.show()

        self.hbox159 = gtk.HBox(False, 0)
        self.hbox159.show()
        self.hbox159.set_spacing(2)

        self.image62 = gtk.Image()
        self.image62.set_from_stock(gtk.STOCK_ADD, 4)
        self.image62.show()
        self.hbox159.pack_start(self.image62, False, False, 0)

        self.label241 = gtk.Label(_("Add..."))
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

        self.hbox160 = gtk.HBox(False, 0)
        self.hbox160.show()
        self.hbox160.set_spacing(2)

        self.image63 = gtk.Image()
        self.image63.set_from_stock(gtk.STOCK_REMOVE, 4)
        self.image63.show()
        self.hbox160.pack_start(self.image63, False, False, 0)

        self.label242 = gtk.Label(_("Remove"))
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

        self.hbox161 = gtk.HBox(False, 0)
        self.hbox161.show()
        self.hbox161.set_spacing(2)

        self.image64 = gtk.Image()
        self.image64.set_from_stock(gtk.STOCK_CLEAR, 4)
        self.image64.show()
        self.hbox161.pack_start(self.image64, False, False, 0)

        self.label243 = gtk.Label(_("Clear"))
        self.label243.show()
        self.hbox161.pack_start(self.label243, False, False, 0)

        self.alignment67.add(self.hbox161)

        self.button79.add(self.alignment67)

        self.vbox97.pack_start(self.button79, False, False, 0)

        self.hbox141.pack_start(self.vbox97)

        self.vbox91.pack_start(self.hbox141)

        self.hbox146 = gtk.HBox(False, 0)
        self.hbox146.show()

        self.UseCustomBan = gtk.CheckButton()
        self.UseCustomBan.set_label(_("Use custom ban message:"))
        self.UseCustomBan.show()
        self.UseCustomBan.connect("toggled", self.OnUseCustomBanToggled)
        self.hbox146.pack_start(self.UseCustomBan, False, False, 0)

        self.CustomBan = gtk.Entry()
        self.CustomBan.show()
        self.hbox146.pack_start(self.CustomBan)

        self.vbox91.pack_start(self.hbox146, False, False, 0)

        self.Main.add(self.vbox91)

        self.label218 = gtk.Label(_("Banning"))
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
            self.SearchFrame = gtk.Window()
            self.SearchFrame.set_title(_("Search"))
            self.SearchFrame.add_accel_group(self.accel_group)
            self.SearchFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()

        self.vbox93 = gtk.VBox(False, 0)
        self.vbox93.show()
        self.vbox93.set_spacing(10)
        self.vbox93.set_border_width(5)

        self.label262 = gtk.Label(_("Network Searches:"))
        self.label262.set_alignment(0, 0)
        self.label262.show()
        self.vbox93.pack_start(self.label262, False, False, 0)

        self.hbox147 = gtk.HBox(False, 0)
        self.hbox147.show()
        self.hbox147.set_spacing(5)

        self.label225 = gtk.Label(_("Send out a max of"))
        self.label225.set_alignment(1, 0.50)
        self.label225.show()
        self.hbox147.pack_start(self.label225, False, False, 0)

        self.MaxResults = gtk.Entry()
        self.MaxResults.set_text(_("1"))
        self.MaxResults.show()
        self.MaxResults.set_width_chars(5)
        self.hbox147.pack_start(self.MaxResults, False, True, 0)

        self.label226 = gtk.Label(_("results per search request"))
        self.label226.show()
        self.hbox147.pack_start(self.label226, False, False, 0)

        self.vbox93.pack_start(self.hbox147, False, False, 0)

        self.label263 = gtk.Label(_("Your Searches:"))
        self.label263.set_alignment(0, 0.50)
        self.label263.show()
        self.vbox93.pack_start(self.label263, False, False, 0)

        self.RegexpFilters = gtk.CheckButton()
        self.RegexpFilters.set_label(_("Use regular expressions for filter in & out"))
        self.RegexpFilters.show()
        self.vbox93.pack_start(self.RegexpFilters, False, False, 0)

        self.EnableFilters = gtk.CheckButton()
        self.EnableFilters.set_label(_("Enable filters by default"))
        self.EnableFilters.show()
        self.EnableFilters.connect("toggled", self.OnEnableFiltersToggled)
        self.vbox93.pack_start(self.EnableFilters, False, False, 0)

        self.table4 = gtk.Table()
        self.table4.show()
        self.table4.set_row_spacings(5)
        self.table4.set_col_spacings(5)

        self.hbox164 = gtk.HBox(False, 0)
        self.hbox164.show()

        self.FilterCC = gtk.Entry()
        self.FilterCC.show()
        self.hbox164.pack_start(self.FilterCC, False, True, 0)

        self.table4.attach(self.hbox164, 1, 2, 4, 5, gtk.FILL, gtk.FILL, 0, 0)

        self.label259 = gtk.Label(_("Country:"))
        self.label259.set_alignment(0, 0.50)
        self.label259.show()
        self.table4.attach(self.label259, 0, 1, 4, 5, gtk.FILL, 0, 0, 0)

        self.FilterFree = gtk.CheckButton()
        self.FilterFree.set_label(_("Free slot"))
        self.FilterFree.show()
        self.table4.attach(self.FilterFree, 1, 2, 5, 6, gtk.FILL, 0, 0, 0)

        self.hbox163 = gtk.HBox(False, 0)
        self.hbox163.show()

        self.FilterBR = gtk.Entry()
        self.FilterBR.show()
        self.hbox163.pack_start(self.FilterBR, False, True, 0)

        self.table4.attach(self.hbox163, 1, 2, 3, 4, gtk.FILL, gtk.FILL, 0, 0)

        self.hbox162 = gtk.HBox(False, 0)
        self.hbox162.show()

        self.FilterSize = gtk.Entry()
        self.FilterSize.show()
        self.hbox162.pack_start(self.FilterSize, False, True, 0)

        self.table4.attach(self.hbox162, 1, 2, 2, 3, gtk.FILL, gtk.FILL, 0, 0)

        self.FilterOut = gtk.Entry()
        self.FilterOut.show()
        self.table4.attach(self.FilterOut, 1, 2, 1, 2, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.FilterIn = gtk.Entry()
        self.FilterIn.show()
        self.table4.attach(self.FilterIn, 1, 2, 0, 1, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.label258 = gtk.Label(_("Bitrate:"))
        self.label258.set_alignment(0, 0.50)
        self.label258.show()
        self.table4.attach(self.label258, 0, 1, 3, 4, gtk.FILL, 0, 0, 0)

        self.label257 = gtk.Label(_("Size:"))
        self.label257.set_alignment(0, 0.50)
        self.label257.show()
        self.table4.attach(self.label257, 0, 1, 2, 3, gtk.FILL, 0, 0, 0)

        self.label256 = gtk.Label(_("Filter out:"))
        self.label256.set_alignment(0, 0.50)
        self.label256.show()
        self.table4.attach(self.label256, 0, 1, 1, 2, gtk.FILL, 0, 0, 0)

        self.label255 = gtk.Label(_("Filter in:"))
        self.label255.set_alignment(0, 0.50)
        self.label255.show()
        self.table4.attach(self.label255, 0, 1, 0, 1, gtk.FILL, 0, 0, 0)

        self.vbox93.pack_start(self.table4)

        self.Main.add(self.vbox93)

        self.label224 = gtk.Label(_("Searches"))
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
            self.SettingsWindow = gtk.Window()
            self.SettingsWindow.set_default_size(650, 400)
            self.SettingsWindow.set_title(_("Nicotine Settings"))
            self.SettingsWindow.set_position(gtk.WIN_POS_CENTER)
            self.SettingsWindow.add_accel_group(self.accel_group)

        self.vbox94 = gtk.VBox(False, 0)
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

        self.viewport1 = gtk.Viewport()
        self.viewport1.show()
        self.viewport1.set_shadow_type(gtk.SHADOW_NONE)

        self.scrolledwindow12.add(self.viewport1)

        self.hpaned1.pack2(self.scrolledwindow12, True, True)

        self.vbox94.pack_start(self.hpaned1)

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
            self.AwayFrame = gtk.Window()
            self.AwayFrame.set_title(_("Away"))
            self.AwayFrame.add_accel_group(self.accel_group)
            self.AwayFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()

        self.vbox95 = gtk.VBox(False, 0)
        self.vbox95.show()
        self.vbox95.set_spacing(10)
        self.vbox95.set_border_width(5)

        self.hbox105 = gtk.HBox(False, 0)
        self.hbox105.show()

        self.label170 = gtk.Label(_("Toggle away after "))
        self.label170.set_alignment(0, 0.50)
        self.label170.show()
        self.hbox105.pack_start(self.label170, False, False, 0)

        self.AutoAway = gtk.Entry()
        self.AutoAway.set_text(_("15"))
        self.AutoAway.show()
        self.AutoAway.set_width_chars(3)
        self.hbox105.pack_start(self.AutoAway, False, False, 0)

        self.label171 = gtk.Label(_(" minutes of inactivity"))
        self.label171.show()
        self.hbox105.pack_start(self.label171, False, False, 0)

        self.vbox95.pack_start(self.hbox105, False, True, 0)

        self.hbox107 = gtk.HBox(False, 0)
        self.hbox107.show()

        self.label174 = gtk.Label(_("Auto-reply when away:  "))
        self.label174.set_alignment(0, 0.50)
        self.label174.show()
        self.hbox107.pack_start(self.label174, False, False, 0)

        self.AutoReply = gtk.Entry()
        self.AutoReply.set_size_request(193, -1)
        self.AutoReply.show()
        self.hbox107.pack_start(self.AutoReply, False, False, 0)

        self.vbox95.pack_start(self.hbox107, False, True, 0)

        self.Main.add(self.vbox95)

        self.label235 = gtk.Label(_("Away mode"))
        self.label235.show()
        self.Main.set_label_widget(self.label235)


        if create:
            self.AwayFrame.add(self.Main)

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class EventsFrame:
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
            self.EventsFrame = gtk.Window()
            self.EventsFrame.set_title(_("Events"))
            self.EventsFrame.add_accel_group(self.accel_group)
            self.EventsFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()

        self.vbox96 = gtk.VBox(False, 0)
        self.vbox96.show()
        self.vbox96.set_spacing(10)
        self.vbox96.set_border_width(5)

        self.ShowNotification = gtk.CheckButton()
        self.ShowNotification.set_label(_("Show notification popup in tray after each download\n(requires python-notify and notification-daemon)"))
        self.ShowNotification.show()
        self.vbox96.pack_start(self.ShowNotification, False, True, 0)

        self.label214 = gtk.Label(_("Run command after download finishes ($ for filename):"))
        self.label214.set_alignment(0, 0.50)
        self.label214.show()
        self.vbox96.pack_start(self.label214, False, False, 0)

        self.AfterDownload = gtk.Entry()
        self.AfterDownload.set_size_request(313, -1)
        self.AfterDownload.show()
        self.vbox96.pack_start(self.AfterDownload, False, False, 0)

        self.label215 = gtk.Label(_("Run command after folder finishes ($ for folder path):"))
        self.label215.set_alignment(0, 0.50)
        self.label215.set_size_request(48, -1)
        self.label215.show()
        self.vbox96.pack_start(self.label215, False, False, 0)

        self.AfterFolder = gtk.Entry()
        self.AfterFolder.set_size_request(313, -1)
        self.AfterFolder.show()
        self.vbox96.pack_start(self.AfterFolder, False, False, 0)

        self.label376 = gtk.Label(_("File Manager command ($ for folder path):"))
        self.label376.set_alignment(0, 0.50)
        self.label376.show()
        self.vbox96.pack_start(self.label376, False, False, 0)

        self.FileManagerCombo_List = gtk.ListStore(gobject.TYPE_STRING)
        self.FileManagerCombo = gtk.ComboBoxEntry()
        self.FileManagerCombo.show()

        self.comboboxentry_entry5 = self.FileManagerCombo.child

        self.FileManagerCombo.set_model(self.FileManagerCombo_List)
        self.FileManagerCombo.set_text_column(0)
        self.vbox96.pack_start(self.FileManagerCombo, False, True, 0)

        self.Main.add(self.vbox96)

        self.label236 = gtk.Label(_("Events"))
        self.label236.show()
        self.Main.set_label_widget(self.label236)


        if create:
            self.EventsFrame.add(self.Main)

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class GeoBlockFrame:
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
            self.GeoBlockFrame = gtk.Window()
            self.GeoBlockFrame.set_title(_("GeoBlock"))
            self.GeoBlockFrame.add_accel_group(self.accel_group)
            self.GeoBlockFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()

        self.vbox98 = gtk.VBox(False, 0)
        self.vbox98.show()
        self.vbox98.set_spacing(10)
        self.vbox98.set_border_width(5)

        self.GeoBlock = gtk.CheckButton()
        self.GeoBlock.set_label(_("Enable geographical blocker"))
        self.GeoBlock.show()
        self.GeoBlock.connect("toggled", self.OnGeoBlockToggled)
        self.vbox98.pack_start(self.GeoBlock, False, False, 0)

        self.GeoPanic = gtk.CheckButton()
        self.GeoPanic.set_label(_("Geographical paranoia (block unresolvable IPs)"))
        self.GeoPanic.show()
        self.vbox98.pack_start(self.GeoPanic, False, False, 0)

        self.label245 = gtk.Label(_("Country codes to block (comma separated):"))
        self.label245.set_alignment(0, 0.50)
        self.label245.show()
        self.vbox98.pack_start(self.label245, False, False, 0)

        self.GeoBlockCC = gtk.Entry()
        self.GeoBlockCC.show()
        self.vbox98.pack_start(self.GeoBlockCC, False, False, 0)

        self.Main.add(self.vbox98)

        self.label244 = gtk.Label(_("Geographical Blocking"))
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
            self.UrlCatchFrame = gtk.Window()
            self.UrlCatchFrame.set_title(_("UrlCatch"))
            self.UrlCatchFrame.add_accel_group(self.accel_group)
            self.UrlCatchFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()

        self.vbox99 = gtk.VBox(False, 0)
        self.vbox99.show()
        self.vbox99.set_spacing(10)
        self.vbox99.set_border_width(5)

        self.URLCatching = gtk.CheckButton()
        self.URLCatching.set_label(_("Enable URL catching"))
        self.URLCatching.show()
        self.URLCatching.connect("toggled", self.OnURLCatchingToggled)
        self.vbox99.pack_start(self.URLCatching, False, False, 0)

        self.HumanizeURLs = gtk.CheckButton()
        self.HumanizeURLs.set_label(_("Humanize slsk:// urls"))
        self.HumanizeURLs.show()
        self.vbox99.pack_start(self.HumanizeURLs, False, False, 0)

        self.label251 = gtk.Label(_("Protocols handlers:"))
        self.label251.set_alignment(0, 0.50)
        self.label251.show()
        self.vbox99.pack_start(self.label251, False, False, 0)

        self.scrolledwindow14 = gtk.ScrolledWindow()
        self.scrolledwindow14.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolledwindow14.show()

        self.ProtocolHandlers = gtk.TreeView()
        self.ProtocolHandlers.show()
        self.scrolledwindow14.add(self.ProtocolHandlers)

        self.vbox99.pack_start(self.scrolledwindow14)

        self.table3 = gtk.Table()
        self.table3.show()

        self.Handler_List = gtk.ListStore(gobject.TYPE_STRING)
        self.Handler = gtk.ComboBoxEntry()
        self.Handler.show()

        self.comboboxentry_entry6 = self.Handler.child

        self.Handler.set_model(self.Handler_List)
        self.Handler.set_text_column(0)
        self.table3.attach(self.Handler, 1, 2, 1, 2, gtk.FILL, gtk.FILL, 0, 0)

        self.button87 = gtk.Button()
        self.button87.show()
        self.button87.connect("clicked", self.OnRemove)

        self.alignment75 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment75.show()

        self.hbox175 = gtk.HBox(False, 0)
        self.hbox175.show()
        self.hbox175.set_spacing(2)

        self.image69 = gtk.Image()
        self.image69.set_from_stock(gtk.STOCK_REMOVE, 4)
        self.image69.show()
        self.hbox175.pack_start(self.image69, False, False, 0)

        self.label298 = gtk.Label(_("Remove"))
        self.label298.show()
        self.hbox175.pack_start(self.label298, False, False, 0)

        self.alignment75.add(self.hbox175)

        self.button87.add(self.alignment75)

        self.table3.attach(self.button87, 2, 3, 1, 2, gtk.FILL, 0, 0, 0)

        self.button86 = gtk.Button()
        self.button86.show()
        self.button86.connect("clicked", self.OnUpdate)

        self.alignment74 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment74.show()

        self.hbox174 = gtk.HBox(False, 0)
        self.hbox174.show()
        self.hbox174.set_spacing(2)

        self.image68 = gtk.Image()
        self.image68.set_from_stock(gtk.STOCK_REDO, 4)
        self.image68.show()
        self.hbox174.pack_start(self.image68, False, False, 0)

        self.label297 = gtk.Label(_("Update"))
        self.label297.show()
        self.hbox174.pack_start(self.label297, False, False, 0)

        self.alignment74.add(self.hbox174)

        self.button86.add(self.alignment74)

        self.table3.attach(self.button86, 2, 3, 0, 1, gtk.FILL, 0, 0, 0)

        self.label253 = gtk.Label(_("Handler:"))
        self.label253.set_alignment(0, 0.50)
        self.label253.show()
        self.table3.attach(self.label253, 0, 1, 1, 2, gtk.FILL, 0, 0, 0)

        self.Protocol = gtk.Entry()
        self.tooltips.set_tip(self.Protocol, _("Example: http"))
        self.Protocol.show()
        self.table3.attach(self.Protocol, 1, 2, 0, 1, gtk.EXPAND|gtk.FILL, 0, 0, 0)

        self.label252 = gtk.Label(_("Protocol:"))
        self.label252.set_alignment(0, 0.50)
        self.label252.show()
        self.table3.attach(self.label252, 0, 1, 0, 1, gtk.FILL, 0, 0, 0)

        self.vbox99.pack_start(self.table3)

        self.Main.add(self.vbox99)

        self.label246 = gtk.Label(_("URL Catching:"))
        self.label246.show()
        self.Main.set_label_widget(self.label246)


        if create:
            self.UrlCatchFrame.add(self.Main)

    def OnURLCatchingToggled(self, widget):
        pass

    def OnRemove(self, widget):
        pass

    def OnUpdate(self, widget):
        pass

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class ConnectionFrame:
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
            self.ConnectionFrame = gtk.Window()
            self.ConnectionFrame.set_title(_("Connection"))
            self.ConnectionFrame.add_accel_group(self.accel_group)
            self.ConnectionFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()

        self.alignment68 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment68.show()

        self.vbox100 = gtk.VBox(False, 0)
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
        self.label286.show()
        self.vbox100.pack_start(self.label286, False, False, 0)

        self.label287 = gtk.Label(_("http://www.maxmind.com/app/python"))
        self.label287.set_alignment(0, 0)
        self.label287.set_padding(8, 0)
        self.label287.show()
        self.vbox100.pack_start(self.label287, False, False, 0)

        self.alignment68.add(self.vbox100)

        self.Main.add(self.alignment68)

        self.label266 = gtk.Label("")
        self.label266.set_markup(_("Connection Settings"))
        self.label266.show()
        self.Main.set_label_widget(self.label266)


        if create:
            self.ConnectionFrame.add(self.Main)

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class UIFrame:
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
            self.UIFrame = gtk.Window()
            self.UIFrame.set_title(_("UI"))
            self.UIFrame.add_accel_group(self.accel_group)
            self.UIFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()

        self.alignment69 = gtk.Alignment(0, 0, 0, 0)
        self.alignment69.show()

        self.vbox101 = gtk.VBox(False, 0)
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

        self.label276 = gtk.Label("")
        self.label276.set_markup(_("User Interface Settings"))
        self.label276.show()
        self.Main.set_label_widget(self.label276)


        if create:
            self.UIFrame.add(self.Main)

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class MiscFrame:
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
            self.MiscFrame = gtk.Window()
            self.MiscFrame.set_title(_("Misc"))
            self.MiscFrame.add_accel_group(self.accel_group)
            self.MiscFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()

        self.alignment70 = gtk.Alignment(0, 0, 0, 0)
        self.alignment70.show()

        self.vbox102 = gtk.VBox(False, 0)
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

        self.label279 = gtk.Label("")
        self.label279.set_markup(_("Miscellaneous Settings"))
        self.label279.show()
        self.Main.set_label_widget(self.label279)


        if create:
            self.MiscFrame.add(self.Main)

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class ImportFrame:
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
            self.ImportFrame = gtk.Window()
            self.ImportFrame.set_title(_("Import Config"))
            self.ImportFrame.add_accel_group(self.accel_group)
            self.ImportFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()

        self.vbox112 = gtk.VBox(False, 0)
        self.vbox112.show()
        self.vbox112.set_spacing(10)
        self.vbox112.set_border_width(5)

        self.label354 = gtk.Label(_("Importing the config files from the official client will overwrite some of your settings (Login, Password, User Info, User Image). Use caution with this feature."))
        self.label354.set_alignment(0, 0.50)
        self.label354.set_line_wrap(True)
        self.label354.show()
        self.vbox112.pack_start(self.label354, False, False, 0)

        self.label356 = gtk.Label(_("Select the directory that contains slsk.exe and the .cfg files: Ex: C:\\Program Files\\SoulSeek"))
        self.label356.set_alignment(0, 0.50)
        self.label356.set_line_wrap(True)
        self.label356.show()
        self.vbox112.pack_start(self.label356, False, False, 0)

        self.hbox203 = gtk.HBox(False, 0)
        self.hbox203.show()
        self.hbox203.set_spacing(5)
        self.hbox203.set_border_width(3)

        self.ImportPath = gtk.Entry()
        self.ImportPath.set_size_request(313, -1)
        self.ImportPath.show()
        self.hbox203.pack_start(self.ImportPath)

        self.ImportDirectory = gtk.Button()
        self.ImportDirectory.show()
        self.ImportDirectory.connect("clicked", self.OnImportDirectory)

        self.alignment91 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment91.show()

        self.hbox204 = gtk.HBox(False, 0)
        self.hbox204.show()
        self.hbox204.set_spacing(2)

        self.image85 = gtk.Image()
        self.image85.set_from_stock(gtk.STOCK_OPEN, 4)
        self.image85.show()
        self.hbox204.pack_start(self.image85, False, False, 0)

        self.ImportDir = gtk.Label(_("Import Directory"))
        self.ImportDir.show()
        self.hbox204.pack_start(self.ImportDir, False, False, 0)

        self.alignment91.add(self.hbox204)

        self.ImportDirectory.add(self.alignment91)

        self.hbox203.pack_end(self.ImportDirectory, False, False, 0)

        self.vbox112.pack_start(self.hbox203, False, True, 0)

        self.hbox205 = gtk.HBox(False, 0)
        self.hbox205.show()
        self.hbox205.set_spacing(5)
        self.hbox205.set_border_width(3)

        self.ImportQueue = gtk.CheckButton()
        self.ImportQueue.set_label(_("Queue"))
        self.ImportQueue.show()
        self.hbox205.pack_start(self.ImportQueue, False, False, 0)

        self.ImportLogin = gtk.CheckButton()
        self.ImportLogin.set_label(_("Login / Password"))
        self.ImportLogin.show()
        self.hbox205.pack_start(self.ImportLogin, False, False, 0)

        self.ImportRooms = gtk.CheckButton()
        self.ImportRooms.set_label(_("Joined Chat Rooms"))
        self.ImportRooms.show()
        self.hbox205.pack_start(self.ImportRooms, False, False, 0)

        self.vbox112.pack_start(self.hbox205, False, True, 0)

        self.hbox206 = gtk.HBox(False, 0)
        self.hbox206.show()
        self.hbox206.set_spacing(5)
        self.hbox206.set_border_width(3)

        self.ImportBuddyList = gtk.CheckButton()
        self.ImportBuddyList.set_label(_("Buddy List"))
        self.ImportBuddyList.show()
        self.hbox206.pack_start(self.ImportBuddyList, False, False, 0)

        self.ImportBanList = gtk.CheckButton()
        self.ImportBanList.set_label(_("Banned List"))
        self.ImportBanList.show()
        self.hbox206.pack_start(self.ImportBanList, False, False, 0)

        self.ImportIgnoreList = gtk.CheckButton()
        self.ImportIgnoreList.set_label(_("Ignored List"))
        self.ImportIgnoreList.show()
        self.hbox206.pack_start(self.ImportIgnoreList, False, False, 0)

        self.ImportUserInfo = gtk.CheckButton()
        self.ImportUserInfo.set_label(_("User Info"))
        self.ImportUserInfo.show()
        self.hbox206.pack_start(self.ImportUserInfo, False, False, 0)

        self.ImportUserImage = gtk.CheckButton()
        self.ImportUserImage.set_label(_("User Image"))
        self.ImportUserImage.show()
        self.hbox206.pack_start(self.ImportUserImage, False, False, 0)

        self.vbox112.pack_start(self.hbox206, False, True, 0)

        self.hbox207 = gtk.HBox(False, 0)
        self.hbox207.show()
        self.hbox207.set_spacing(5)
        self.hbox207.set_border_width(3)

        self.label358 = gtk.Label(_("Restart Nicotine to see all changes take effect"))
        self.label358.show()
        self.hbox207.pack_start(self.label358, False, False, 0)

        self.ImportConfig = gtk.Button()
        self.ImportConfig.show()
        self.ImportConfig.connect("clicked", self.OnImportConfig)

        self.alignment92 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment92.show()

        self.hbox208 = gtk.HBox(False, 0)
        self.hbox208.show()
        self.hbox208.set_spacing(2)

        self.image86 = gtk.Image()
        self.image86.set_from_stock(gtk.STOCK_EXECUTE, 4)
        self.image86.show()
        self.hbox208.pack_start(self.image86, False, False, 0)

        self.label357 = gtk.Label(_("Import Config"))
        self.label357.show()
        self.hbox208.pack_start(self.label357, False, False, 0)

        self.alignment92.add(self.hbox208)

        self.ImportConfig.add(self.alignment92)

        self.hbox207.pack_end(self.ImportConfig, False, False, 0)

        self.vbox112.pack_start(self.hbox207, False, False, 0)

        self.Main.add(self.vbox112)

        self.label353 = gtk.Label(_("Import Config"))
        self.label353.show()
        self.Main.set_label_widget(self.label353)


        if create:
            self.ImportFrame.add(self.Main)

    def OnImportDirectory(self, widget):
        pass

    def OnImportConfig(self, widget):
        pass

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class SoundsFrame:
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
            self.SoundsFrame = gtk.Window()
            self.SoundsFrame.set_title(_("Sounds"))
            self.SoundsFrame.add_accel_group(self.accel_group)
            self.SoundsFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()

        self.vbox119 = gtk.VBox(False, 0)
        self.vbox119.show()
        self.vbox119.set_spacing(5)
        self.vbox119.set_border_width(5)

        self.SoundCheck = gtk.CheckButton()
        self.SoundCheck.set_label(_("Enable Sound Effects"))
        self.SoundCheck.show()
        self.SoundCheck.connect("toggled", self.OnSoundCheckToggled)
        self.vbox119.pack_start(self.SoundCheck, False, False, 0)

        self.hbox228 = gtk.HBox(False, 0)
        self.hbox228.show()
        self.hbox228.set_spacing(5)

        self.sndcmdLabel = gtk.Label(_("Sound Effects command:"))
        self.sndcmdLabel.show()
        self.hbox228.pack_start(self.sndcmdLabel, False, False, 0)

        self.SoundCommand_List = gtk.ListStore(gobject.TYPE_STRING)
        self.SoundCommand = gtk.ComboBoxEntry()
        self.SoundCommand.show()

        self.comboboxentry_entry7 = self.SoundCommand.child

        self.SoundCommand.set_model(self.SoundCommand_List)
        self.SoundCommand.set_text_column(0)
        self.hbox228.pack_start(self.SoundCommand)

        self.DefaultSoundCommand = gtk.Button()
        self.DefaultSoundCommand.show()

        self.alignment103 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment103.show()

        self.hbox229 = gtk.HBox(False, 0)
        self.hbox229.show()
        self.hbox229.set_spacing(2)

        self.image97 = gtk.Image()
        self.image97.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image97.show()
        self.hbox229.pack_start(self.image97, False, False, 0)

        self.label383 = gtk.Label(_("Default"))
        self.label383.show()
        self.hbox229.pack_start(self.label383, False, False, 0)

        self.alignment103.add(self.hbox229)

        self.DefaultSoundCommand.add(self.alignment103)

        self.hbox228.pack_start(self.DefaultSoundCommand, False, False, 0)

        self.vbox119.pack_start(self.hbox228, False, True, 0)

        self.hbox230 = gtk.HBox(False, 0)
        self.hbox230.show()
        self.hbox230.set_spacing(5)

        self.snddirLabel = gtk.Label(_("Sound Effects Directory:"))
        self.snddirLabel.show()
        self.hbox230.pack_start(self.snddirLabel, False, False, 0)

        self.vbox119.pack_start(self.hbox230, False, True, 0)

        self.hbox1 = gtk.HBox(False, 0)
        self.hbox1.show()
        self.hbox1.set_spacing(5)

        self.SoundDirectory = gtk.Entry()
        self.SoundDirectory.show()
        self.hbox1.pack_start(self.SoundDirectory)

        self.SoundButton = gtk.Button()
        self.SoundButton.show()

        self.alignment1 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment1.show()

        self.hbox2 = gtk.HBox(False, 0)
        self.hbox2.show()
        self.hbox2.set_spacing(2)

        self.image1 = gtk.Image()
        self.image1.set_from_stock(gtk.STOCK_OPEN, 4)
        self.image1.show()
        self.hbox2.pack_start(self.image1, False, False, 0)

        self.label1 = gtk.Label(_("Select"))
        self.label1.show()
        self.hbox2.pack_start(self.label1, False, False, 0)

        self.alignment1.add(self.hbox2)

        self.SoundButton.add(self.alignment1)

        self.hbox1.pack_end(self.SoundButton, False, False, 0)

        self.vbox119.pack_start(self.hbox1, False, True, 0)

        self.label421 = gtk.Label(_("Audio Player Command ($ for filename):"))
        self.label421.set_alignment(0, 0.50)
        self.label421.show()
        self.vbox119.pack_start(self.label421, False, False, 5)

        self.audioPlayerCombo_List = gtk.ListStore(gobject.TYPE_STRING)
        self.audioPlayerCombo = gtk.ComboBoxEntry()
        self.audioPlayerCombo.show()

        self.comboboxentry_entry8 = self.audioPlayerCombo.child

        self.audioPlayerCombo.set_model(self.audioPlayerCombo_List)
        self.audioPlayerCombo.set_text_column(0)
        self.vbox119.pack_start(self.audioPlayerCombo, False, True, 0)

        self.Main.add(self.vbox119)

        self.label420 = gtk.Label("")
        self.label420.set_markup(_("<b>Sounds:</b>"))
        self.label420.show()
        self.Main.set_label_widget(self.label420)


        if create:
            self.SoundsFrame.add(self.Main)

    def OnSoundCheckToggled(self, widget):
        pass

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

class IconsFrame:
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
            self.IconsFrame = gtk.Window()
            self.IconsFrame.set_title(_("Icons"))
            self.IconsFrame.add_accel_group(self.accel_group)
            self.IconsFrame.show()

        self.Main = gtk.Frame()
        self.Main.show()

        self.vbox125 = gtk.VBox(False, 0)
        self.vbox125.show()
        self.vbox125.set_spacing(5)
        self.vbox125.set_border_width(5)

        self.TabClosers = gtk.CheckButton()
        self.TabClosers.set_label(_("Close-buttons on tabs (requires restart)"))
        self.TabClosers.show()
        self.vbox125.pack_start(self.TabClosers, False, False, 0)

        self.hbox258 = gtk.HBox(False, 0)
        self.hbox258.show()
        self.hbox258.set_spacing(10)

        self.TrayiconCheck = gtk.CheckButton()
        self.TrayiconCheck.set_label(_("Display Tray Icon"))
        self.TrayiconCheck.show()
        self.hbox258.pack_start(self.TrayiconCheck, False, False, 0)

        self.vbox125.pack_start(self.hbox258, False, False, 0)

        self.hbox261 = gtk.HBox(False, 0)
        self.hbox261.show()

        self.label424 = gtk.Label(_("Icon Theme Directory (requires restart):"))
        self.label424.show()
        self.hbox261.pack_start(self.label424, False, False, 0)

        self.vbox125.pack_start(self.hbox261, False, False, 0)

        self.hbox262 = gtk.HBox(False, 0)
        self.hbox262.show()
        self.hbox262.set_spacing(5)

        self.ThemeButton = gtk.Button()
        self.ThemeButton.show()

        self.alignment128 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment128.show()

        self.hbox263 = gtk.HBox(False, 0)
        self.hbox263.show()
        self.hbox263.set_spacing(2)

        self.image122 = gtk.Image()
        self.image122.set_from_stock(gtk.STOCK_OPEN, 4)
        self.image122.show()
        self.hbox263.pack_start(self.image122, False, False, 0)

        self.label425 = gtk.Label(_("Select"))
        self.label425.show()
        self.hbox263.pack_start(self.label425, False, False, 0)

        self.alignment128.add(self.hbox263)

        self.ThemeButton.add(self.alignment128)

        self.hbox262.pack_start(self.ThemeButton, False, False, 0)

        self.IconTheme = gtk.Entry()
        self.IconTheme.show()
        self.hbox262.pack_start(self.IconTheme)

        self.DefaultTheme = gtk.Button()
        self.DefaultTheme.show()

        self.alignment154 = gtk.Alignment(0.5, 0.5, 0, 0)
        self.alignment154.show()

        self.hbox294 = gtk.HBox(False, 0)
        self.hbox294.show()
        self.hbox294.set_spacing(2)

        self.image148 = gtk.Image()
        self.image148.set_from_stock(gtk.STOCK_CANCEL, 4)
        self.image148.show()
        self.hbox294.pack_start(self.image148, False, False, 0)

        self.label465 = gtk.Label(_("Default"))
        self.label465.show()
        self.hbox294.pack_start(self.label465, False, False, 0)

        self.alignment154.add(self.hbox294)

        self.DefaultTheme.add(self.alignment154)

        self.hbox262.pack_start(self.DefaultTheme, False, True, 0)

        self.vbox125.pack_start(self.hbox262, False, True, 0)

        self.label466 = gtk.Label(_("Current Icons:"))
        self.label466.set_alignment(0, 0.50)
        self.label466.show()
        self.vbox125.pack_start(self.label466, False, False, 0)

        self.table6 = gtk.Table()
        self.table6.show()
        self.table6.set_border_width(3)
        self.table6.set_row_spacings(3)
        self.table6.set_col_spacings(10)

        self.label477 = gtk.Label("")
        self.label477.set_alignment(0, 0.50)
        self.label477.set_markup(_("<b>Status</b>"))
        self.label477.show()
        self.table6.attach(self.label477, 0, 1, 0, 1, gtk.FILL, 0, 0, 0)

        self.label467 = gtk.Label(_("Online:"))
        self.label467.set_alignment(0, 0.50)
        self.label467.show()
        self.table6.attach(self.label467, 0, 1, 1, 2, gtk.FILL, 0, 0, 0)

        self.label468 = gtk.Label(_("Away:"))
        self.label468.set_alignment(0, 0.50)
        self.label468.show()
        self.table6.attach(self.label468, 0, 1, 2, 3, gtk.FILL, 0, 0, 0)

        self.label469 = gtk.Label(_("Offline:"))
        self.label469.set_alignment(0, 0.50)
        self.label469.show()
        self.table6.attach(self.label469, 0, 1, 3, 4, gtk.FILL, 0, 0, 0)

        self.Online = gtk.Image()
        self.Online.set_from_stock(gtk.STOCK_MISSING_IMAGE, 4)
        self.Online.show()
        self.table6.attach(self.Online, 1, 2, 1, 2, gtk.FILL, gtk.FILL, 0, 0)

        self.Away = gtk.Image()
        self.Away.set_from_stock(gtk.STOCK_MISSING_IMAGE, 4)
        self.Away.show()
        self.table6.attach(self.Away, 1, 2, 2, 3, gtk.FILL, gtk.FILL, 0, 0)

        self.Offline = gtk.Image()
        self.Offline.set_from_stock(gtk.STOCK_MISSING_IMAGE, 4)
        self.Offline.show()
        self.table6.attach(self.Offline, 1, 2, 3, 4, gtk.FILL, gtk.FILL, 0, 0)

        self.Hilite = gtk.Image()
        self.Hilite.set_from_stock(gtk.STOCK_MISSING_IMAGE, 4)
        self.Hilite.show()
        self.table6.attach(self.Hilite, 1, 2, 4, 5, gtk.FILL, gtk.FILL, 0, 0)

        self.label474 = gtk.Label(_("Hilite:"))
        self.label474.set_alignment(0, 0.50)
        self.label474.show()
        self.table6.attach(self.label474, 0, 1, 4, 5, gtk.FILL, 0, 0, 0)

        self.N = gtk.Image()
        self.N.set_from_stock(gtk.STOCK_MISSING_IMAGE, 4)
        self.N.show()
        self.table6.attach(self.N, 1, 2, 5, 6, gtk.FILL, gtk.FILL, 0, 0)

        self.label473 = gtk.Label(_("Window:"))
        self.label473.set_alignment(0, 0.50)
        self.label473.show()
        self.table6.attach(self.label473, 0, 1, 5, 6, gtk.FILL, 0, 0, 0)

        self.Connect = gtk.Image()
        self.Connect.set_from_stock(gtk.STOCK_MISSING_IMAGE, 4)
        self.Connect.show()
        self.table6.attach(self.Connect, 3, 4, 1, 2, gtk.FILL, gtk.FILL, 0, 0)

        self.Away2 = gtk.Image()
        self.Away2.set_from_stock(gtk.STOCK_MISSING_IMAGE, 4)
        self.Away2.show()
        self.table6.attach(self.Away2, 3, 4, 3, 4, gtk.FILL, gtk.FILL, 0, 0)

        self.Hilite2 = gtk.Image()
        self.Hilite2.set_from_stock(gtk.STOCK_MISSING_IMAGE, 4)
        self.Hilite2.show()
        self.table6.attach(self.Hilite2, 3, 4, 4, 5, gtk.FILL, gtk.FILL, 0, 0)

        self.Disconnect = gtk.Image()
        self.Disconnect.set_from_stock(gtk.STOCK_MISSING_IMAGE, 4)
        self.Disconnect.show()
        self.table6.attach(self.Disconnect, 3, 4, 2, 3, gtk.FILL, gtk.FILL, 0, 0)

        self.label475 = gtk.Label(_("Hilite:"))
        self.label475.set_alignment(0, 0.50)
        self.label475.show()
        self.table6.attach(self.label475, 2, 3, 4, 5, gtk.FILL, 0, 0, 0)

        self.label470 = gtk.Label(_("Away:"))
        self.label470.set_alignment(0, 0.50)
        self.label470.show()
        self.table6.attach(self.label470, 2, 3, 3, 4, gtk.FILL, 0, 0, 0)

        self.label471 = gtk.Label(_("Disconnected:"))
        self.label471.set_alignment(0, 0.50)
        self.label471.show()
        self.table6.attach(self.label471, 2, 3, 2, 3, gtk.FILL, 0, 0, 0)

        self.label472 = gtk.Label(_("Connected:"))
        self.label472.set_alignment(0, 0.50)
        self.label472.show()
        self.table6.attach(self.label472, 2, 3, 1, 2, gtk.FILL, 0, 0, 0)

        self.label476 = gtk.Label("")
        self.label476.set_alignment(0, 0.50)
        self.label476.set_markup(_("<b>Trayicon</b>"))
        self.label476.show()
        self.table6.attach(self.label476, 2, 3, 0, 1, gtk.FILL, 0, 0, 0)

        self.vbox125.pack_start(self.table6)

        self.Main.add(self.vbox125)

        self.label464 = gtk.Label(_("Extra stuff for your comfort"))
        self.label464.show()
        self.Main.set_label_widget(self.label464)


        if create:
            self.IconsFrame.add(self.Main)

    def get_custom_widget(self, id, string1, string2, int1, int2):
        w = gtk.Label(_("(custom widget: %s)") % id)
        return w

