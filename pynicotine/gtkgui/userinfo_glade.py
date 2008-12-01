import gtk, gobject
from pynicotine.utils import _

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
		self.eventbox1.connect("button_press_event", self.OnImageClick)

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

		self.alignment24 = gtk.Alignment(0, 0.5, 0, 0)
		self.alignment24.show()

		self.hbox44 = gtk.HBox(False, 0)
		self.hbox44.show()
		self.hbox44.set_spacing(2)

		self.image24 = gtk.Image()
		self.image24.set_alignment(0, 0.50)
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

		self.alignment25 = gtk.Alignment(0, 0.5, 0, 0)
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

		self.alignment26 = gtk.Alignment(0, 0.5, 0, 0)
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

		self.alignment37 = gtk.Alignment(0, 0.5, 0, 0)
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

		self.alignment32 = gtk.Alignment(0, 0.5, 0, 0)
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

		self.alignment29 = gtk.Alignment(0, 0.5, 0, 0)
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

		self.alignment30 = gtk.Alignment(0, 0.5, 0, 0)
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

		self.alignment31 = gtk.Alignment(0, 0.5, 0, 0)
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

	def OnImageClick(self, widget):
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

