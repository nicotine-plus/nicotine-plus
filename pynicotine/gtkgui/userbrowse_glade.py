import gtk, gobject
from pynicotine.utils import _

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
		self.hbox61.set_spacing(5)

		self.ExpandButton = gtk.ToggleButton()
		self.tooltips.set_tip(self.ExpandButton, _("Expand / Collapse all"))
		self.ExpandButton.show()
		self.ExpandButton.connect("clicked", self.OnExpand)

		self.ExpandDirectoriesImage = gtk.Image()
		self.ExpandDirectoriesImage.set_from_stock(gtk.STOCK_ADD, 4)
		self.ExpandDirectoriesImage.show()
		self.ExpandButton.add(self.ExpandDirectoriesImage)

		self.hbox61.pack_start(self.ExpandButton, False, False, 0)

		self.NumDirectories = gtk.Label(_("Dirs: Unknown"))
		self.NumDirectories.set_alignment(0, 0.50)
		self.NumDirectories.show()
		self.hbox61.pack_start(self.NumDirectories, False, True, 0)

		self.AmountShared = gtk.Label(_("Shared: Unknown"))
		self.AmountShared.set_alignment(0, 0.50)
		self.AmountShared.show()
		self.hbox61.pack_start(self.AmountShared)

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

