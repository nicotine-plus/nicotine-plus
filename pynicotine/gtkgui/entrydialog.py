# Stolen from dkuhlman's example
#
import gtk
import os
from pynicotine.utils import version
import imagedata

from pynicotine.utils import _


class MetaDialog( gtk.Dialog):
	def __init__(self, frame, message="", data=None, modal= True):
		gtk.Dialog.__init__(self)
		self.connect("destroy", self.quit)
		self.connect("delete_event", self.quit)
		self.nicotine = frame
		if modal:
			self.set_modal(True)
		self.box = gtk.VBox(spacing=10)
		self.box.set_border_width(10)
		self.box.show()
		self.vbox.pack_start(self.box)
		
		if message:
			label = gtk.Label()
			label.set_markup(message)
			label.set_line_wrap(False)
			self.box.pack_start(label, False, False)
			label.show()
			label.set_alignment(0, 0.5)

		self.current = 0
		self.data = data
		

		hbox2 = gtk.HBox(spacing=5)
		hbox2.show()
	
		self.UF = gtk.Frame()
		self.UF.show()
		self.UF.set_shadow_type(gtk.SHADOW_ETCHED_IN)
		self.box.pack_start(self.UF, False, False)
		
		vbox3 = gtk.VBox(spacing=5)
		vbox3.set_border_width(5)
		vbox3.show()
		
		self.UF.add(vbox3)
		
		self.Username = self.MakeLabelStaticEntry( hbox2, "<b>Username:</b>", "", expand=False)
		self.BrowseUser = self.nicotine.CreateIconButton(gtk.STOCK_HARDDISK, "stock", self.OnBrowseUser, _("Browse"))
		hbox2.pack_start(self.BrowseUser, False, False)
		self.Position = self.MakeLabelStaticEntry( hbox2, "<b>List Position:</b>", "", expand=False, width=7, xalign=1)
		
		vbox3.pack_start(hbox2, False, False)
		
		
		
		hbox3 = gtk.HBox(spacing=5)
		hbox3.show()
		vbox3.pack_start(hbox3, False, False)

		self.Filename = self.MakeLabelStaticEntry( hbox3, _("<b>File Name:</b>"), "", fill=True)
		
		
		hbox5 = gtk.HBox(spacing=5)
		hbox5.show()
		vbox3.pack_start(hbox5, False, False)

		self.Directory = self.MakeLabelStaticEntry( hbox5, _("<b>Directory:</b>"), "", fill=True)
		
		self.Media = gtk.Frame()
		self.Media.show()
		self.Media.set_shadow_type(gtk.SHADOW_ETCHED_IN)
		hbox6 = gtk.HBox(spacing=5, homogeneous=False)
        	hbox6.set_border_width(5)
		hbox6.show()

		self.Size = self.MakeLabelStaticEntry( hbox6, _("<b>File Size:</b>"), "", expand=False, width=11, xalign=1)
		self.Length = self.MakeLabelStaticEntry( hbox6, _("<b>Length:</b>"), "", expand=False, width=7, xalign=0.5)
		self.Bitrate = self.MakeLabelStaticEntry( hbox6, _("<b>Bitrate:</b>"), "", expand=False, width=12, xalign=0.5)
		
		self.Media.add(hbox6)
		self.box.pack_start(self.Media, False, False)

		hbox7 = gtk.HBox(spacing=5, homogeneous=False)
		hbox7.show()
		self.box.pack_start(hbox7, False, False)
	
		
		self.Immediate = self.MakeLabelStaticEntry( hbox7, _("<b>Immediate Downloads:</b>"), "", expand=False, width=6, xalign=0.5)
		
		self.Queue = self.MakeLabelStaticEntry( hbox7, _("<b>Queue:</b>"), "", expand=False, width=6, xalign=1)


		hbox4 = gtk.HBox(spacing=5, homogeneous=False)
		hbox4.show()
		self.box.pack_start(hbox4, False, False)

		self.Speed = self.MakeLabelStaticEntry( hbox4, _("<b>Last Speed:</b>"), "", expand=False, width=11, xalign=1)
		
		self.Country = gtk.Label()
		self.Country.hide()
		
		hbox4.pack_start(self.Country, False, False)

		
		self.buttonbox = gtk.HBox(False, 2)
		self.buttonbox.show()
		self.buttonbox.set_spacing(2)
		
		self.box.pack_start(self.buttonbox, False, False)
		
		# Download Button
		self.DownloadItem = self.nicotine.CreateIconButton(gtk.STOCK_GO_DOWN, "stock", self.OnDownloadItem, _("Download"))
		self.buttonbox.pack_start(self.DownloadItem, False, False)
		# Download All Button
		
		self.DownloadAll = self.nicotine.CreateIconButton(gtk.STOCK_GO_DOWN, "stock", self.OnDownloadAll, _("Download All"))
		self.buttonbox.pack_start(self.DownloadAll, False, False)
		self.Selected = self.MakeLabel( self.buttonbox, "<b>%s</b> File(s) Selected" % len(self.data.keys()),  expand=False,  xalign=1)
		self.Previous = self.nicotine.CreateIconButton(gtk.STOCK_GO_BACK, "stock", self.OnPrevious, _("Previous"))
		self.buttonbox.pack_start(self.Previous, False, False)
		self.Next = self.nicotine.CreateIconButton(gtk.STOCK_GO_FORWARD, "stock", self.OnNext, _("Next"))
		self.buttonbox.pack_start(self.Next, False, False)

		button = self.nicotine.CreateIconButton(gtk.STOCK_CLOSE, "stock", self.click, _("Close"))

		button.set_flags(gtk.CAN_DEFAULT)
		self.action_area.pack_start(button)

		button.grab_default()

		self.ret = None
		
		self.Display(self.current)
		
	def OnDownloadItem(self, widget):
		meta = self.data[self.current]

		self.nicotine.np.transfers.getFile(meta["user"], meta["fn"], "")
		
	def OnBrowseUser(self, widget):
		meta = self.data[self.current]
		self.nicotine.BrowseUser(meta["user"])
		
	def OnDownloadAll(self, widget):
		for item, meta in self.data.items():
			self.nicotine.np.transfers.getFile(meta["user"], meta["fn"], "")
			
	def OnPrevious(self, widget):

		if len(self.data.keys()) > 1:
			_list = self.data.keys()
			if not self.current in _list:
				ix -= 1
			else:
				ix = _list.index(self.current)

				ix -= 1

					
				if ix < 0:
					ix = -1
				elif ix >= len(_list):
					ix = 0
			if ix != None:
				self.current = _list[ix]
		if self.current == None:
			return
		self.Display(self.current)
		
	def OnNext(self, widget):
		if len(self.data.keys()) > 1: 
			_list = self.data.keys()
			if not self.current in _list:
				ix += 1
			else:
				ix = _list.index(self.current)

				ix += 1

					
				if ix < 0:
					ix = -1
				elif ix >= len(_list):
					ix = 0
			if ix != None:
				self.current = _list[ix]
		if self.current == None:
			return
		self.Display(self.current)
		
	def Display(self, item):
		if not self.data.has_key(item):
			return
		self.current = item
		
		More = False
		if len(self.data.keys()) > 1:
			More = True
		self.Next.set_sensitive(More)
		self.Previous.set_sensitive(More)
		self.DownloadAll.set_sensitive(More)
		
		self.Username.set_text	(self.data[self.current]["user"])
		self.Filename.set_text	(self.data[self.current]["filename"])
		self.Directory.set_text	(self.data[self.current]["directory"])
		self.Size.set_text	(str(self.data[self.current]["size"]))
		self.Speed.set_text	(self.data[self.current]["speed"])
		self.Position.set_text	(str(self.data[self.current]["position"]))
		if self.data[self.current]["bitrate"] not in ("", None):
			self.Bitrate.set_text(self.data[self.current]["bitrate"] + " Kbps")
		else:
			self.Bitrate.set_text("")
		self.Length.set_text	(self.data[self.current]["length"])
		self.Queue.set_text	(self.data[self.current]["queue"])
		self.Immediate.set_text	(str(self.data[self.current]["immediate"] == "Y"))
		
		if self.data[self.current]["country"] not in ("", None):
			self.Country.set_markup("<b>Country Code:</b> "+self.data[self.current]["country"] )
			self.Country.show()
		else:
			self.Country.set_text("")
			self.Country.hide()
		
	def quit(self, w=None, event=None):
		self.hide()
		self.destroy()
		gtk.main_quit()
	def click(self, button):

		self.quit()
	
	def MakeLabel(self, parent, labeltitle, expand=True, fill=False, xalign=0):
		
		label = gtk.Label()
		label.set_markup(labeltitle)
		label.show()
		#label.set_property("selectable", True)
		parent.pack_start(label, False, False)

		try:label.set_property("xalign", xalign)
		except:pass

		return label
		
	def MakeLabelStaticEntry(self, parent, labeltitle, entrydata, editable=False, expand=True, fill=False, width=-1, xalign=0):
		
		label = gtk.Label()
		label.set_markup(labeltitle)
		label.show()

		parent.pack_start(label, False, False)
		
		entry = gtk.Entry()
		entry.set_property("editable", editable)
		entry.set_property("width-chars", width)
		try:entry.set_property("xalign", xalign)
		except:pass
		entry.show()
		if entrydata is not None:
			entry.set_text(entrydata)
		parent.pack_start(entry, expand, fill)
		return entry
		
class EntryDialog( gtk.Dialog):
	def __init__(self, frame, message="", default_text='', modal= True, option=False, optionmessage="", optionvalue=False, droplist=[]):
		gtk.Dialog.__init__(self)
		self.connect("destroy", self.quit)
		self.connect("delete_event", self.quit)
		self.gotoption = option
		if modal:
			self.set_modal(True)
		box = gtk.VBox(spacing=10)
		box.set_border_width(10)
		self.vbox.pack_start(box)
		box.show()
		if message:
			label = gtk.Label(message)
			box.pack_start(label, False, False)
			label.set_line_wrap(True)
			label.show()
		self.combo = gtk.combo_box_entry_new_text()
		for i in droplist:
			self.combo.append_text( i)
		self.combo.child.set_text(default_text)
	
		box.pack_start(self.combo, False, False)
		self.combo.show()
		self.combo.grab_focus()
		
		
		self.option = gtk.CheckButton()
		self.option.set_active(optionvalue)
		self.option.set_label(optionmessage)
		self.option.show()
		if self.gotoption:
			box.pack_start(self.option, False, False)
		button = gtk.Button(_("OK"))
		button.connect("clicked", self.click)
		button.set_flags(gtk.CAN_DEFAULT)
		self.action_area.pack_start(button)
		button.show()
		button.grab_default()
		button = gtk.Button(_("Cancel"))
		button.connect("clicked", self.quit)
		button.set_flags(gtk.CAN_DEFAULT)
		self.action_area.pack_start(button)
		button.show()
		self.ret = None
	def quit(self, w=None, event=None):
		self.hide()
		self.destroy()
		gtk.main_quit()
	def click(self, button):
		if self.gotoption:
			self.ret = [self.combo.child.get_text(), self.option.get_active()]
		else:
			self.ret = self.combo.child.get_text()
		self.quit()

def input_box(frame, title="Input Box", message="", default_text='', 
	modal= True, option=False, optionmessage="", optionvalue=False, droplist=[]):

	win = EntryDialog(frame, message, default_text, modal=modal, option=option, optionmessage=optionmessage, optionvalue=optionvalue, droplist=droplist)
	win.set_title(title)
	win.set_icon(frame.images["n"])
	win.set_default_size(300, 100)
	win.show()
	gtk.main()
	return win.ret


def Option_Box(frame, title="Option Box", message="", default_text='', 
	modal= True, option1="", option2="", option3="", status=None ):
	
	win = OptionDialog(frame, message, modal=modal, option3=option3, option1=option1, option2=option2, status=status)
	win.set_title(title)
	win.set_icon(frame.images["n"])
	win.show()
	gtk.main()
	return win.ret

class OptionDialog( gtk.Dialog):
	def __init__(self, frame, message="",modal= False, option1="", option2="", option3="", status=None):
		gtk.Dialog.__init__(self)
		self.connect("destroy", self.quit)
		self.connect("delete_event", self.quit)
		
		self.set_modal(modal)
		box = gtk.VBox(spacing=10)
		box.set_border_width(10)
		self.vbox.pack_start(box)
		box.show()
		hbox = gtk.HBox(spacing=5)
		hbox.set_border_width(5)
		hbox.show()
		box.pack_start(hbox)
		if status:
			image = gtk.Image()
			image.set_padding(0, 0)
			if status == "warning":
				icon = gtk.STOCK_DIALOG_WARNING
			else:
				icon = gtk.STOCK_DIALOG_QUESTION
			image.set_from_stock(icon, 4)
			image.show()
			hbox.pack_start(image)
		if message:
			label = gtk.Label(message)
			hbox.pack_start(label)
			label.set_line_wrap(True)
			label.show()
		
			
		if option1 is not None:
			button1 = gtk.Button(option1)
			button1.connect("clicked", self.option1)
			button1.set_flags(gtk.CAN_DEFAULT)
			self.action_area.pack_start(button1)
			button1.show()
		if option2 is not None:
			button2 = gtk.Button(option2)
			button2.connect("clicked", self.option2)
			button2.set_flags(gtk.CAN_DEFAULT)
			self.action_area.pack_start(button2)
			button2.show()
			button2.grab_default()
		if option3 is not None:
			button3 = gtk.Button(option3)
			button3.connect("clicked", self.option3)
			button3.set_flags(gtk.CAN_DEFAULT)
			self.action_area.pack_start(button3)
			button3.show()
			self.ret = None
        
	def quit(self, w=None, event=None):
		self.hide()
		self.destroy()
		gtk.main_quit()
		
	def option3(self, button3):
		self.ret = 3
		self.quit()
		
	def option1(self, button1):
		self.ret = 1
		self.quit()
		
	def option2(self, button2):
		self.ret = 2
		self.quit()