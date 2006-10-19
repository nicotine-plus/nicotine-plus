# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
import gtk
import gobject
import os
import locale
import sys

from utils import recode, InputDialog

from pynicotine.utils import _

def ChooseDir(parent = None, initialdir = "~"):
	dialog = gtk.FileChooserDialog(parent=parent, action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, buttons = (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT, gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))
        dialog.set_action(gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
	dialog.set_select_multiple(True)
        dir = os.path.expanduser(initialdir)
        if os.path.exists(dir):
            dialog.set_current_folder(dir)
        else:
            dialog.set_current_folder(os.path.expanduser("~"))
	response = dialog.run()
	
	if response == gtk.RESPONSE_ACCEPT:
		res = dialog.get_filenames()
	else:
		res = None
	dialog.hide()
	gtk.threads_leave()
	dialog.destroy()
	gtk.threads_enter()
	del dialog
	return res

def ChooseFile(parent = None, initialdir = "~"):
	dialog = gtk.FileChooserDialog(parent=parent, action=gtk.FILE_CHOOSER_ACTION_OPEN, buttons = (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT, gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))
        dialog.set_action(gtk.FILE_CHOOSER_ACTION_OPEN)
	dialog.set_select_multiple(False)
        dir = os.path.expanduser(initialdir)
        if os.path.exists(dir):
            dialog.set_current_folder(dir)
        else:
            dialog.set_current_folder(os.path.expanduser("~"))
	response = dialog.run()
	
	if response == gtk.RESPONSE_ACCEPT:
		res = dialog.get_filenames()
	else:
		res = None
	dialog.hide()
	gtk.threads_leave()
	dialog.destroy()
	gtk.threads_enter()
	del dialog
	return res
	
if __name__ == "__main__":
	print ChooseDir()
	print ChooseFile()
	