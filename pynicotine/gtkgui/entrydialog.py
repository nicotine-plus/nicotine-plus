# Stolen from dkuhlman's example
#
import gtk
import os
from pynicotine.utils import version
import imagedata

from pynicotine.utils import _


class EntryDialog( gtk.Dialog):
    def __init__(self, frame, message="", default_text='', modal= True):
        gtk.Dialog.__init__(self)
        self.connect("destroy", self.quit)
        self.connect("delete_event", self.quit)
	
        if modal:
            self.set_modal(True)
        box = gtk.VBox(spacing=10)
        box.set_border_width(10)
        self.vbox.pack_start(box)
        box.show()
        if message:
            label = gtk.Label(message)
            box.pack_start(label)
            label.show()
	self.combo = gtk.combo_box_entry_new_text()
	for i in frame.np.config.sections["server"]["userlist"]:
		self.combo.append_text( i[0])
	self.combo.child.set_text(default_text)

        box.pack_start(self.combo)
        self.combo.show()
        self.combo.grab_focus()
        button = gtk.Button("OK")
        button.connect("clicked", self.click)
        button.set_flags(gtk.CAN_DEFAULT)
        self.action_area.pack_start(button)
        button.show()
        button.grab_default()
        button = gtk.Button("Cancel")
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
        self.ret = self.combo.child.get_text()
        self.quit()

def input_box(frame, title="Input Box", message="", default_text='',
        modal= True):

    win = EntryDialog(frame, message, default_text, modal=modal)
    win.set_title(title)
    win.show()
    gtk.main()
    return win.ret
