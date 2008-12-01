import gtk, gobject
from pynicotine.utils import _

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

		self.Main = gtk.VBox(False, 0)
		self.Main.show()
		self.Main.set_spacing(1)

		self.hbox6 = gtk.HBox(False, 0)
		self.hbox6.show()
		self.hbox6.set_spacing(5)

		self.QueryLabel = gtk.Label(_("Query"))
		self.QueryLabel.set_alignment(0, 0.50)
		self.QueryLabel.set_padding(3, 0)
		self.QueryLabel.set_line_wrap(True)
		self.QueryLabel.show()
		self.hbox6.pack_start(self.QueryLabel)

		self.ExpandButton = gtk.ToggleButton()
		self.tooltips.set_tip(self.ExpandButton, _("Expand / Collapse all"))
		self.ExpandButton.set_active(True)
		self.ExpandButton.connect("toggled", self.OnToggleExpandAll)

		self.expandImage = gtk.Image()
		self.expandImage.set_from_stock(gtk.STOCK_REMOVE, 4)
		self.expandImage.show()
		self.ExpandButton.add(self.expandImage)

		self.hbox6.pack_start(self.ExpandButton, False, True, 0)

		self.usersGroup = gtk.CheckButton()
		self.usersGroup.set_label(_("Group by Users"))
		self.usersGroup.show()
		self.usersGroup.connect("toggled", self.OnGroup)

		self.hbox6.pack_start(self.usersGroup, False, True, 0)

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

		self.ClearButton = gtk.Button()
		self.tooltips.set_tip(self.ClearButton, _("Clear all results"))
		self.ClearButton.show()
		self.ClearButton.connect("clicked", self.OnClear)

		self.clearImage = gtk.Image()
		self.clearImage.set_from_stock(gtk.STOCK_CLEAR, 4)
		self.clearImage.show()
		self.ClearButton.add(self.clearImage)

		self.hbox6.pack_start(self.ClearButton, False, False, 0)

		self.IgnoreButton = gtk.Button()
		self.tooltips.set_tip(self.IgnoreButton, _("Stop new search results from being displayed"))
		self.IgnoreButton.show()
		self.IgnoreButton.connect("clicked", self.OnIgnore)

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

		self.IgnoreButton.add(self.alignment36)

		self.hbox6.pack_start(self.IgnoreButton, False, False, 0)

		self.CloseButton = gtk.Button()
		self.tooltips.set_tip(self.CloseButton, _("Close search tab; press ignore to prevent this tab from reopening"))
		self.CloseButton.show()
		self.CloseButton.connect("clicked", self.OnClose)

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

		self.CloseButton.add(self.alignment35)

		self.hbox6.pack_start(self.CloseButton, False, False, 0)

		self.Main.pack_start(self.hbox6, False, True, 3)

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

		self.Main.pack_start(self.Filters, False, True, 3)

		self.scrolledwindow17 = gtk.ScrolledWindow()
		self.scrolledwindow17.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.scrolledwindow17.show()
		self.scrolledwindow17.set_shadow_type(gtk.SHADOW_IN)

		self.ResultsList = gtk.TreeView()
		self.ResultsList.show()
		self.scrolledwindow17.add(self.ResultsList)

		self.Main.pack_start(self.scrolledwindow17)


		if create:
			self.SearchTab.add(self.Main)

	def OnToggleExpandAll(self, widget):
		pass

	def OnGroup(self, widget):
		pass

	def OnToggleFilters(self, widget):
		pass

	def OnToggleRemember(self, widget):
		pass

	def OnClear(self, widget):
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

