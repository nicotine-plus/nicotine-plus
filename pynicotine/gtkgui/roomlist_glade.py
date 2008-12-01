import gtk, gobject
from pynicotine.utils import _

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
		self.vbox2.set_spacing(3)

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
		self.hbox1.set_spacing(3)

		self.label10 = gtk.Label(_("Create: "))
		self.label10.show()
		self.hbox1.pack_start(self.label10, False, True, 0)

		self.CreateRoomEntry = gtk.Entry()
		self.CreateRoomEntry.show()
		self.CreateRoomEntry.connect("activate", self.OnCreateRoom)
		self.hbox1.pack_start(self.CreateRoomEntry)

		self.HideRoomList = gtk.Button()
		self.tooltips.set_tip(self.HideRoomList, _("Hide room list"))
		self.HideRoomList.show()

		self.alignment27 = gtk.Alignment(0.5, 0.5, 0, 0)
		self.alignment27.show()

		self.image7 = gtk.Image()
		self.image7.set_from_stock(gtk.STOCK_REMOVE, 4)
		self.image7.show()
		self.alignment27.add(self.image7)

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

