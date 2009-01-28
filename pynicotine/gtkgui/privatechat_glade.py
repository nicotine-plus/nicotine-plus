import gtk, gobject
from pynicotine.utils import _

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
		self.ChatScroll.set_wrap_mode(gtk.WRAP_WORD_CHAR)
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

