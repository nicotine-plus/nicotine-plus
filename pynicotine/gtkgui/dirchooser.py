# Copyright (C) 2007 daelstorm. All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Original copyright below
# Copyright (c) 2003-2004 Hyriand. All rights reserved.

import gtk
import gobject
import os
import locale
import sys

from utils import recode, InputDialog


def ChooseDir(parent = None, initialdir = "~", create=False, name=None, title=None):
	dialog = gtk.FileChooserDialog(title=title, parent=parent, action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
	if create:
		dialog.set_action(gtk.FILE_CHOOSER_ACTION_CREATE_FOLDER)
	else:
		dialog.set_action(gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
		dialog.set_select_multiple(True)
	
	dir = os.path.expanduser(initialdir)
	if os.path.exists(dir):
		dialog.set_current_folder(dir)
	else:
		dialog.set_current_folder(os.path.expanduser("~"))
	if name:
		dialog.set_current_name(name)
	response = dialog.run()

	if response == gtk.RESPONSE_ACCEPT:
		res = dialog.get_filenames()
	else:
		res = None

	dialog.destroy()

	return res

def ChooseFile(parent = None, initialdir = "~", initialfile = "", multiple = False):
	dialog = gtk.FileChooserDialog(parent=parent, action=gtk.FILE_CHOOSER_ACTION_OPEN, buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
	dialog.set_action(gtk.FILE_CHOOSER_ACTION_OPEN)
	dialog.set_select_multiple(multiple)
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

	dialog.destroy()

	return res

def SaveFile(parent = None, initialdir = "~", initialfile = "", title=None):
	dialog = gtk.FileChooserDialog(parent=parent, action=gtk.FILE_CHOOSER_ACTION_SAVE, buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
	dialog.set_action(gtk.FILE_CHOOSER_ACTION_SAVE)
	dialog.set_select_multiple(False)
	dialog.set_show_hidden(True)
	if title:
		dialog.set_title(title)
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

	dialog.destroy()

	return res

def ChooseImage(parent = None, initialdir = "~", initialfile = "", title=None):
	image = gtk.Image()
	preview = gtk.ScrolledWindow()
	preview.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
	preview.set_size_request(200, -1)
	preview.add_with_viewport(image)
	image.show()
	preview.show()
	dialog = gtk.FileChooserDialog(title=title, parent=parent, action=gtk.FILE_CHOOSER_ACTION_OPEN, buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
	dialog.set_action(gtk.FILE_CHOOSER_ACTION_OPEN)
	dialog.set_select_multiple(False)
	dialog.set_preview_widget(preview)
	dialog.connect("update-preview", update_preview_cb, preview)
	dir, file = os.path.split(initialfile)
	dir = os.path.expanduser(dir)
	if os.path.exists(dir):
		dialog.set_current_folder(dir)
	else:
		dialog.set_current_folder(os.path.expanduser("~"))
	response = dialog.run()
	
	if response == gtk.RESPONSE_ACCEPT:
		res = dialog.get_filenames()
	else:
		res = None

	dialog.destroy()

	return res

def update_preview_cb(file_chooser, preview):
	filename = file_chooser.get_preview_filename()
	try:
		if filename:
			pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
			preview.child.child.set_from_pixbuf(pixbuf)
			have_preview = True
		else:
			have_preview = False
	except Exception, e:
		#print e
		have_preview = False
	file_chooser.set_preview_widget_active(have_preview)
	return	
		
if __name__ == "__main__":
	print ChooseDir()
	print ChooseFile()
	
