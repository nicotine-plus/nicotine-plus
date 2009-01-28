import gtk, gobject
from pynicotine.utils import _

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

		self.Speech = gtk.ToggleButton()
		self.tooltips.set_tip(self.Speech, _("Toggle Text-To-Speech"))
		self.Speech.set_active(True)
		self.Speech.show()

		self.alignment45 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment45.show()

		self.hbox48 = gtk.HBox(False, 0)
		self.hbox48.show()

		self.SpeechIcon = gtk.Image()
		self.SpeechIcon.set_from_stock(gtk.STOCK_MEDIA_PLAY, 4)
		self.SpeechIcon.show()
		self.hbox48.pack_start(self.SpeechIcon, False, False, 0)

		self.alignment45.add(self.hbox48)

		self.Speech.add(self.alignment45)

		self.hbox7.pack_end(self.Speech, False, False, 0)

		self.HideUserList = gtk.ToggleButton()
		self.tooltips.set_tip(self.HideUserList, _("Hide/Show User list"))
		self.HideUserList.show()
		self.HideUserList.connect("toggled", self.OnHideUserList)

		self.alignment47 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment47.show()

		self.hbox70 = gtk.HBox(False, 0)
		self.hbox70.show()

		self.HideUserListImage = gtk.Image()
		self.HideUserListImage.set_from_stock(gtk.STOCK_GO_FORWARD, 4)
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
		self.HideStatusLogImage.set_from_stock(gtk.STOCK_GO_UP, 4)
		self.HideStatusLogImage.show()
		self.hbox67.pack_start(self.HideStatusLogImage, False, False, 0)

		self.alignment44.add(self.hbox67)

		self.HideStatusLog.add(self.alignment44)

		self.hbox7.pack_end(self.HideStatusLog, False, False, 0)

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
		self.ChatScroll.set_wrap_mode(gtk.WRAP_WORD_CHAR)
		self.ChatScroll.set_cursor_visible(False)
		self.ChatScroll.set_editable(False)
		self.ChatScroll.show()
		self.ChatScrollWindow.add(self.ChatScroll)

		self.vbox6.pack_start(self.ChatScrollWindow)

		self.ChatEntryBox = gtk.HBox(False, 0)
		self.ChatEntryBox.show()

		self.ChatEntry = gtk.Entry()
		self.ChatEntry.show()
		self.ChatEntry.connect("activate", self.OnEnter)
		self.ChatEntry.connect("key_press_event", self.OnKeyPress)
		self.ChatEntryBox.pack_start(self.ChatEntry)

		self.ShowChatHelp = gtk.Button()
		self.tooltips.set_tip(self.ShowChatHelp, _("Chat room command help"))
		self.ShowChatHelp.show()
		self.ShowChatHelp.connect("clicked", self.OnShowChatHelp)

		self.alignment28 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment28.show()

		self.hbox47 = gtk.HBox(False, 0)
		self.hbox47.show()

		self.image39 = gtk.Image()
		self.image39.set_from_stock(gtk.STOCK_HELP, 4)
		self.image39.show()
		self.hbox47.pack_start(self.image39, False, False, 0)

		self.alignment28.add(self.hbox47)

		self.ShowChatHelp.add(self.alignment28)

		self.ChatEntryBox.pack_end(self.ShowChatHelp, False, False, 0)

		self.vbox6.pack_start(self.ChatEntryBox, False, False, 0)

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

	def OnEnter(self, widget):
		pass

	def OnKeyPress(self, widget):
		pass

	def OnShowChatHelp(self, widget):
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

