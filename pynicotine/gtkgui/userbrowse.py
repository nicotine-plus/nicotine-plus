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

from __future__ import division

import gtk
import os, sys
import urllib
import gobject
import gc
from userinfo import UserTabs

from utils import InitialiseColumns, PopupMenu, EncodingsMenu, SaveEncoding, Humanize, HumanizeBytes, PressHeader
from dirchooser import ChooseDir
from entrydialog import *
from pynicotine import slskmessages
from thread import start_new_thread

from pynicotine.utils import _, displayTraceback, executeCommand

class UserBrowse:
	def __init__(self, userbrowses, user, conn):
		self.wTree = gtk.glade.XML(os.path.join(os.path.dirname(os.path.realpath(__file__)), "userbrowse.glade" ), None, "nicotine" ) 
		widgets = self.wTree.get_widget_prefix("")
		for i in widgets:
			name = gtk.glade.get_widget_name(i)
			self.__dict__[name] = i
		self.UserBrowseTab.remove(self.Main)
		self.UserBrowseTab.destroy()
		#UserBrowseTab.__init__(self, False)
		self.wTree.signal_autoconnect(self)
		self.userbrowses = userbrowses

		self.frame = userbrowses.frame
		self.tooltips = self.frame.tooltips
		if not self.frame.np.config.sections["ui"]["tooltips"]:
			self.tooltips.disable()
		self.user = user
		self.conn = conn
		self.selected_folder = None
		self.search_list = []
		self.query = None
		self.search_position = 0
		self.selected_files = []
		
		self.shares = {}
		self.Elist = {}
		# Iters for current DirStore
		self.directories = {}
		# Iters for current FileStore
		self.files = {}
		self.totalsize = 0
		self.encoding, m = EncodingsMenu(self.frame.np, "userencoding", user)
		
		self.EncodingStore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
		self.Encoding.set_size_request(100, -1)
		self.Encoding.set_model(self.EncodingStore)
		cell = gtk.CellRendererText()
		self.Encoding.pack_start(cell, True)
		self.Encoding.add_attribute(cell, 'text', 0)
		cell2 = gtk.CellRendererText()
		self.Encoding.pack_start(cell2, False)
	
		self.Encoding.add_attribute(cell2, 'text', 1)
		
		for item in m:
			self.Elist[item[1]] = self.EncodingStore.append([item[1], item[0] ])
			if self.encoding == item[1]:
				self.Encoding.set_active_iter(self.Elist[self.encoding])
		
		self.DirStore = gtk.TreeStore(  str, str )
		self.FolderTreeView.set_model(self.DirStore)

		self.FolderTreeView.set_headers_visible(True)
		self.DirStore.set_sort_column_id(0, gtk.SORT_ASCENDING)
		# GTK 2.10
		if gtk.pygtk_version[0] >= 2 and gtk.pygtk_version[1] >= 10:
			self.FolderTreeView.set_enable_tree_lines(True)

		cols = InitialiseColumns(self.FolderTreeView,
			[_("Directories"), -1, "text", self.CellDataFunc], #0
		)
		cols[0].set_sort_column_id(0)
		
		self.popup_menu_users = PopupMenu(self.frame)
		self.popup_menu_users2 = PopupMenu(self.frame)
		for menu in [self.popup_menu_users, self.popup_menu_users2]:
			menu.setup( 
				("#" + _("Send _message"), menu.OnSendMessage, gtk.STOCK_EDIT),
				("#" + _("Show IP a_ddress"), menu.OnShowIPaddress, gtk.STOCK_NETWORK),
				("#" + _("Get user i_nfo"), menu.OnGetUserInfo, gtk.STOCK_DIALOG_INFO),
				("#" + _("Gi_ve privileges"), menu.OnGivePrivileges, gtk.STOCK_JUMP_TO),
				("", None),
				("$" + _("_Add user to list"),  menu.OnAddToList),
				("$" + _("_Ban this user"), menu.OnBanUser),
				("$" + _("_Ignore this user"), menu.OnIgnoreUser),
			)
		
		self.popup_menu_downloads_folders = PopupMenu(self.frame)
		self.popup_menu_downloads_folders.setup( 
			("#" + _("_Download directory"), self.OnDownloadDirectory, gtk.STOCK_GO_DOWN),
			("#" + _("Download directory _to..."), self.OnDownloadDirectoryTo, gtk.STOCK_GO_DOWN),
			("#" + _("Download _recursive"), self.OnDownloadDirectoryRecursive, gtk.STOCK_GO_DOWN),
			("#" + _("Download r_ecursive to..."), self.OnDownloadDirectoryRecursiveTo, gtk.STOCK_GO_DOWN),
		)
		self.popup_menu_downloads_files = PopupMenu(self.frame)
		self.popup_menu_downloads_files.setup( 
			("#" + _("_Download file(s)"), self.OnDownloadFiles, gtk.STOCK_GO_DOWN),
			("#" + _("Download _to..."), self.OnDownloadFilesTo, gtk.STOCK_GO_DOWN),
			("", None),
			("#" + _("_Download directory"), self.OnDownloadDirectory, gtk.STOCK_GO_DOWN),
			("#" + _("Download directory _to..."), self.OnDownloadDirectoryTo, gtk.STOCK_GO_DOWN),
			("#" + _("Download _recursive"), self.OnDownloadDirectoryRecursive, gtk.STOCK_GO_DOWN),
			("#" + _("Download r_ecursive to..."), self.OnDownloadDirectoryRecursiveTo, gtk.STOCK_GO_DOWN),
		)
				
		self.popup_menu_uploads_folders = PopupMenu(self.frame)
		self.popup_menu_uploads_folders.setup( 
			("#" + _("Upload Directory to..."), self.OnUploadDirectoryTo, gtk.STOCK_GO_UP),
			("#" + _("Upload Directory recursive to..."), self.OnUploadDirectoryRecursiveTo, gtk.STOCK_GO_UP),
		)
		
		self.popup_menu_uploads_files = PopupMenu(self.frame)
		self.popup_menu_uploads_files.setup( 
			("#" + _("Upload Directory to..."), self.OnUploadDirectoryTo, gtk.STOCK_GO_UP),
			("#" + _("Upload Directory recursive to..."), self.OnUploadDirectoryRecursiveTo, gtk.STOCK_GO_UP),
			("#" + _("Up_load file(s)"), self.OnUploadFiles, gtk.STOCK_GO_UP),
		)
		
		self.folder_popup_menu  = PopupMenu(self.frame)
		self.folder_popup_menu.set_user(user)
		if user == self.frame.np.config.sections["server"]["login"]:
			self.folder_popup_menu.setup(
				("USERMENU", _("User"), self.popup_menu_users, self.OnPopupMenuFolderUser),
				("", None),
				(2, _("Download"), self.popup_menu_downloads_folders, self.OnPopupMenuDummy, gtk.STOCK_GO_DOWN),
				(2, _("Upload"), self.popup_menu_uploads_folders, self.OnPopupMenuDummy, gtk.STOCK_GO_UP),
				("", None),
				("#" + _("Copy _URL"), self.OnCopyDirURL, gtk.STOCK_COPY),
				("#" + _("Open in File Manager"), self.OnFileManager, gtk.STOCK_OPEN),
			)
		else:
			self.folder_popup_menu.setup(
				("USERMENU", _("User"), self.popup_menu_users, self.OnPopupMenuFolderUser),
				("", None),
				(2, _("Download"), self.popup_menu_downloads_folders, self.OnPopupMenuDummy, gtk.STOCK_GO_DOWN),
				("", None),
				("#" + _("Copy _URL"), self.OnCopyDirURL, gtk.STOCK_COPY),
			)
		
		self.FolderTreeView.connect("button_press_event", self.OnFolderClicked)
		self.FolderTreeView.get_selection().connect("changed", self.OnSelectDir)
		
		# DecodedFilename, HSize, Bitrate, HLength, Size, Length, RawFilename
		self.FileStore = gtk.ListStore(str, str, str, str, gobject.TYPE_INT64, int, str)

		self.FileTreeView.set_model(self.FileStore)
		cols = InitialiseColumns(self.FileTreeView,
			[_("Filename"), 250, "text", self.CellDataFunc],
			[_("Size"), 100, "number", self.CellDataFunc],
			[_("Bitrate"), 70, "text", self.CellDataFunc],
			[_("Length"), 50, "number", self.CellDataFunc],
		)
		cols[0].set_sort_column_id(0)
		cols[1].set_sort_column_id(4)
		cols[2].set_sort_column_id(2)
		cols[3].set_sort_column_id(5)
		self.FileStore.set_sort_column_id(0, gtk.SORT_ASCENDING)
		for i in range (4):
			parent = cols[i].get_widget().get_ancestor(gtk.Button)
			if parent:
				parent.connect('button_press_event', PressHeader)
			# Read Show / Hide column settings from last session
		self.FileTreeView.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

		self.FileTreeView.set_headers_clickable(True)
		self.FileTreeView.set_property("rules-hint", True)
		
		self.file_popup_menu = PopupMenu(self.frame)
		
		if user == self.frame.np.config.sections["server"]["login"]:
			self.file_popup_menu.setup(
				("USERMENU", "User", self.popup_menu_users2, self.OnPopupMenuFileUser),
				("", None),
				(2, _("Download"), self.popup_menu_downloads_files, self.OnPopupMenuDummy, gtk.STOCK_GO_DOWN),
				(2, _("Upload"), self.popup_menu_uploads_files, self.OnPopupMenuDummy, gtk.STOCK_GO_UP),
				("", None),
				("#" + _("Copy _URL"), self.OnCopyURL, gtk.STOCK_COPY),
				("#" + _("Send to _player"), self.OnPlayFiles, gtk.STOCK_MEDIA_PLAY),
				("#" + _("Open in File Manager"), self.OnFileManager, gtk.STOCK_OPEN),
				
				
			
			)
		else:
			self.file_popup_menu.setup(
				("USERMENU", "User", self.popup_menu_users2, self.OnPopupMenuFileUser),
				("", None),
				(2, _("Download"), self.popup_menu_downloads_files, self.OnPopupMenuDummy, gtk.STOCK_GO_DOWN),
				("", None),
				("#" + _("Copy _URL"), self.OnCopyURL, gtk.STOCK_COPY),
			)
		self.FileTreeView.connect("button_press_event", self.OnFileClicked)
		self.ChangeColours()

		for name, object in self.__dict__.items():
			if type(object) is PopupMenu:
				object.set_user(self.user)
				
	def OnPopupMenuDummy(self, widget, something):
		pass
	
	def Attach(self, widget=None):
		self.userbrowses.attach_tab(self.Main)

		
	def Detach(self, widget=None):
		self.userbrowses.detach_tab(self.Main, _("Nicotine+ User Browse: %s (%s)") % (self.user, [_("Offline"), _("Away"), _("Online")][self.status]))
		
	def ConnClose(self):
		pass
		
	def OnPopupMenuFileUser(self, widget):
		self.OnPopupMenuUsers(self.popup_menu_users2)
		
	def OnPopupMenuFolderUser(self, widget):
		self.OnPopupMenuUsers(self.popup_menu_users)
		
	def OnPopupMenuUsers(self, menu):
		items = menu.get_children()

		act = True
		items[0].set_sensitive(act)
		items[1].set_sensitive(act)
		items[2].set_sensitive(act)

		items[5].set_active(self.user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
		items[6].set_active(self.user in self.frame.np.config.sections["server"]["banlist"])
		items[7].set_active(self.user in self.frame.np.config.sections["server"]["ignorelist"])
		
		for i in range(3, 8):
			items[i].set_sensitive(act)
		return True
		
	def ChangeColours(self):
		self.frame.SetTextBG(self.FileTreeView)
		self.frame.SetTextBG(self.FolderTreeView)
		self.frame.SetTextBG(self.entry4)
		
		self.frame.ChangeListFont(self.FolderTreeView, self.frame.np.config.sections["ui"]["browserfont"])
		self.frame.ChangeListFont(self.FileTreeView, self.frame.np.config.sections["ui"]["browserfont"])

		
	def CellDataFunc(self, column, cellrenderer, model, iter):
		colour = self.frame.np.config.sections["ui"]["search"]
		if colour == "":
			colour = None
		cellrenderer.set_property("foreground", colour)
			
	def decode(self, str):
		return self.frame.np.decode(str, self.encoding)
	
	def OnExpand(self, widget):
		if self.ExpandButton.get_active():
			self.FolderTreeView.expand_all()
			self.ExpandDirectoriesImage.set_from_stock(gtk.STOCK_REMOVE, 4)
		else:
			self.FolderTreeView.collapse_all()
			self.ExpandDirectoriesImage.set_from_stock(gtk.STOCK_ADD, 4)

			dirs = list(self.directories.keys())
			dirs.sort()
			if dirs != []:
				self.SetDirectory(dirs[0])
			else:
				self.SetDirectory(None)
			
	def OnFolderClicked(self, widget, event):
		if event.button == 1 and event.type == gtk.gdk._2BUTTON_PRESS:
			self.OnDownloadDirectory(widget)
			return True
		elif event.button == 3:
			return self.OnFolderPopupMenu(widget, event)
		return False
		
	def OnFolderPopupMenu(self, widget, event):
		act = True
		if self.selected_folder is None:
			act = False
		items = self.folder_popup_menu.get_children()
		for item in items[1:]:
			item.set_sensitive(act)

		self.folder_popup_menu.popup(None, None, None, event.button, event.time)
	
	def SelectedFilesCallback(self, model, path, iter):
		rawfilename = self.FileStore.get_value(iter, 6)
		self.selected_files.append(rawfilename)
	
	def OnFileClicked(self, widget, event):
		if event.button == 1 and event.type == gtk.gdk._2BUTTON_PRESS:
			self.selected_files = []
			self.FileTreeView.get_selection().selected_foreach(self.SelectedFilesCallback)
			self.OnDownloadFiles(widget)
			self.FileTreeView.get_selection().unselect_all()
			return True
		elif event.button == 3:
			return self.OnFilePopupMenu(widget, event)
		return False
			
	def OnFilePopupMenu(self, widget, event):
		self.selected_files = []
		self.FileTreeView.get_selection().selected_foreach(self.SelectedFilesCallback)
		
		files = True
		multiple = False
	
		if len(self.selected_files) > 1:
			multiple = True
		if len(self.selected_files) >= 1:
			files = True
		else:
			files = False
			
		items = self.file_popup_menu.get_children()
		
		if self.user == self.frame.np.config.sections["server"]["login"]:
			items[2].set_sensitive(files) # Downloads
			items[3].set_sensitive(files) # Uploads
			items[5].set_sensitive(not multiple and files) # Copy URL
			items[6].set_sensitive(files) # Send to player
		else:
			items[2].set_sensitive(files) # Downloads
			items[4].set_sensitive(not multiple and files) # Copy URL
			
		self.FileTreeView.emit_stop_by_name("button_press_event")
		self.file_popup_menu.popup(None, None, None, event.button, event.time)
		return True

	def MakeNewModel(self, list):

		self.shares = list
		self.selected_folder = None
		self.selected_files = []
		self.directories.clear()
		self.files.clear()
		self.DirStore.clear()
		
		# Select first directory
		currentdir = self.BrowseGetDirs()
		sel = self.FolderTreeView.get_selection()
		sel.unselect_all()
		if currentdir in  self.directories:
			path = self.DirStore.get_path(self.directories[currentdir])
			if path is not None:
				sel.select_path(path)
				
		self.FolderTreeView.set_sensitive(True)
		self.FileTreeView.set_sensitive(True)
		self.SaveButton.set_sensitive(True)
		
		if self.ExpandButton.get_active():
			self.FolderTreeView.expand_all()
		else:
			self.FolderTreeView.collapse_all()
		
	def BrowseGetDirs(self):
		sorted = list(self.shares.keys())
		sorted.sort()
		self.NumDirectories.set_text(_("Dirs: %s") % len(self.shares))
		children = []
		self.directories.clear()
		directory = ""
		self.totalsize = 0
		dirseparator = '\\'
		if sorted == []:
			self.AmountShared.set_text(_("Shared: %s") % HumanizeBytes(self.totalsize))
			return directory
		for item in sorted:
			s = item.split(dirseparator)
			path = ''

			parent = s[0]
			if parent == '':
				parent += dirseparator
				if parent not in self.directories.keys():
					self.directories[parent] =  self.DirStore.append(None, [self.decode(parent), parent])
			parent = s[0]
			for seq in s[1:]:
				path = dirseparator.join([parent, seq])
				if parent == "":
					parent = dirseparator
				if parent not in self.directories.keys():
					self.directories[parent] =  self.DirStore.append(None, [self.decode(parent), parent])
				if path not in children:
					children.append(path)
					self.directories[path] = self.DirStore.append(self.directories[parent], [self.decode(path.split(dirseparator)[-1]), path ] )
				parent = path
		sortlist = list(self.directories.keys())
		sortlist.sort()
		for files in self.shares.values():
			for filedata in files:
				self.totalsize += filedata[2]
		self.AmountShared.set_text(_("Shared: %s") % HumanizeBytes(self.totalsize))
	
		directory = sortlist[0]
		return directory
	
	def SetDirectory(self, directory):
		self.selected_folder = directory
		self.FileStore.clear()
		self.files.clear()
		if directory not in self.shares:
			return
		
		path = self.DirStore.get_path( self.directories[directory] )

		files = self.shares[directory]

		for file in files:
			# DecodedFilename, HSize, Bitrate, HLength, Size, Length, RawFilename
			rl = 0
			try: size = int(file[2])
			except: size = 0
			f = [self.decode(file[1]), Humanize(size)]
			if file[3] == "":
				f += ["", ""]
			else:
				#file[4] is for file types such as 'mp3'
				attrs = file[4]
				if attrs != [] and type(attrs) is list:
					if len(attrs) >= 3:
						br = str(attrs[0])
						if attrs[2]:
							br = br + _(" (vbr)")
						try: rl = int(attrs[1])
						except: rl = 0
						l = "%i:%02i" % (rl / 60, rl % 60)
						f += [br, l]
					else:
						f += ["", ""]
				else:
					f += ["", ""]
			f += [long(size), rl, file[1]]

			try:
				self.files[f[0]] = self.FileStore.append(f)
			except Exception, error:
				displayTraceback()

	def OnSave(self, widget):
		configdir, config = os.path.split(self.frame.np.config.filename)
		sharesdir = os.path.abspath(configdir+os.sep+"usershares"+os.sep)
			
		try:
			if not os.path.exists(sharesdir):
				os.mkdir(sharesdir)
		except Exception, msg:
			error = _("Can't create directory '%(folder)s', reported error: %(error)s" % {'folder':sharesdir, 'error':msg})
			print error
			self.frame.logMessage(error)
		try:
			import pickle
			import bz2
			sharesfile = bz2.BZ2File(os.path.join(sharesdir, self.encode(self.user)), 'w' )
			pickle.dump(self.shares, sharesfile)
			sharesfile.close()
		except Exception, msg:
			error = _("Can't save shares, '%(user)s', reported error: %(error)s" % {'user':self.user, 'error':msg} )
			print error
			self.frame.logMessage(error)
			
	def encode(self, path):
		try:
			if sys.platform == "win32":
				chars = ["?", "\/", "\"", ":", ">", "<", "|", "*"]
				for char in chars:
					path = path.replace(char, "_")
			return path
		except:
			return path
	
	def ShowInfo(self, msg):
		self.conn = None
		self.MakeNewModel(msg.list)
		
	def LoadShares(self, list):
		self.MakeNewModel(list)
		
	def UpdateGauge(self, msg):
		if msg.total == 0 or msg.bytes == 0:
			fraction = 0.0
		elif msg.bytes >= msg.total:
			fraction = 1.0
		else:
			fraction = float(msg.bytes) / msg.total
		self.progressbar1.set_fraction(fraction)

	def OnSelectDir(self, selection):
		model, iter = selection.get_selected()
		if iter is None:
			self.selected_folder = None
			return
		path = model.get_path(iter)
		directory = self.DirStore.get_value(self.DirStore.get_iter(path), 1)
		self.FolderTreeView.expand_to_path(path)
		self.SetDirectory(directory)
		
	def OnResort(self, column, column_id):
		model = self.FileTreeView.get_model()
		if model.sort_col == column_id:
			order = model.sort_order
			if order == gtk.SORT_ASCENDING:
				order = gtk.SORT_DESCENDING
			else:
				order = gtk.SORT_ASCENDING
			column.set_sort_order(order)
			model.sort_order = order
			self.FileTreeView.set_model(None)
			model.sort()
			self.FileTreeView.set_model(model)
			return
		cols = self.FileTreeView.get_columns()
		cols[model.sort_col].set_sort_indicator(False)
		cols[column_id].set_sort_indicator(True)
		model.sort_col = column_id
		self.OnResort(column, column_id)

	def OnDownloadDirectory(self, widget):
		self.DownloadDirectory(self.selected_folder)
			
	def OnDownloadDirectoryRecursive(self, widget):

		prefix = ""
		dir = self.selected_folder 
		if dir == None:
			return
		localdir = ""
		files = []
		files += self.DownloadDirectoryRecursive(dir, os.path.join(localdir, ""))
		# Check the number of files to be downloaded, just to make sure we aren't accidently downloading hundreds or thousands
		numfiles = len(files)
		go_ahead=0
		if len(files) > 100:
			FolderDownload(self.frame, title=_('Nicotine+')+': Download %(num)i files?' % {'num':numfiles}, message=_("Are you sure you wish to download %(num)i files from %(user)s's directory %(folder)s?" %{ 'num':numfiles, 'user':self.user, 'folder':dir } ), data=files, callback=self.folder_download_response )
		else:
			# Good to go, we download these
			for item in files:
				file, localpath, size, bitrate, length = item
				self.frame.np.transfers.getFile(self.user, file, localpath, size=size, bitrate=bitrate, length=length)
				
	def folder_download_response(self, dialog, response, files):

		if response == gtk.RESPONSE_CANCEL:
			dialog.destroy()
			return
		elif response == gtk.RESPONSE_OK:
			dialog.destroy()
			for item in files:
				file, localpath, size, bitrate, length = item
				self.frame.np.transfers.getFile(self.user, file, localpath, size=size, bitrate=bitrate, length=length)
	
			
	def DownloadDirectoryRecursive(self, dir, prefix = ""):
		# Find all files and add them to list
		if dir == None:
			return
		localdir = prefix + dir.split("\\")[-1]

		files = []
		if dir in self.shares.keys():
			for file in self.shares[dir]:
				length = bitrate = None
				attrs = file[4]
				if attrs != []:
					bitrate = str(attrs[0])
					if attrs[2]:
						bitrate += _(" (vbr)")
					try: rl = int(attrs[1])
					except: rl = 0
					length = "%i:%02i" % (rl // 60, rl % 60)

				files.append(["\\".join([dir, file[1]]), localdir, file[2], bitrate, length])
		for directory in self.shares.keys():
			if dir in directory and dir != directory:
				files += self.DownloadDirectoryRecursive(directory, os.path.join(localdir, ""))
		return files
		
	def OnDownloadDirectoryTo(self, widget):
		if self.selected_folder == None:
			return
		dir = ChooseDir(self.frame.MainWindow, self.frame.np.config.sections["transfers"]["downloaddir"])
		if dir is None:
			return

		for directory in dir: # iterate over selected files
			try:
				self.DownloadDirectory(self.selected_folder, os.path.join(directory, ""))
			except IOError: # failed to open
				self.frame.logMessage('failed to open %r for reading', directory) # notify user

	def OnDownloadDirectoryRecursiveTo(self, widget):
		dir = ChooseDir(self.frame.MainWindow, self.frame.np.config.sections["transfers"]["downloaddir"])
		if dir is None:
			return
		for directory in dir: # iterate over selected files
			try:
				self.DownloadDirectory(self.selected_folder, os.path.join(directory, ""), 1)
			except IOError: # failed to open
				self.frame.logMessage('failed to open %r for reading', directory) # notify user

	
	def DownloadDirectory(self, dir, prefix = "", recurse = 0):
		if dir == None or dir not in self.shares:
			return
		ldir = prefix + dir.split("\\")[-1]
		priorityfiles = []
		normalfiles = []
		if self.frame.np.config.sections["transfers"]["prioritize"]:
			for file in self.shares[dir]:
				(junk, sep, ext) = file[1].rpartition('.')
				if sep and ext in ['sfv','md5','nfo']:
					priorityfiles.append(file)
				else:
					normalfiles.append(file)
		else:
			normalfiles = self.shares[dir][:]
		if self.frame.np.config.sections["transfers"]["reverseorder"]:
			deco = [(x[1], x) for x in normalfiles]
			deco.sort(reverse=True)
			normalfiles = [x for junk, x in deco]
		for file in priorityfiles + normalfiles:
			length = bitrate = None
			attrs = file[4]
			if attrs != []:
				bitrate = str(attrs[0])
				if attrs[2]:
					bitrate += _(" (vbr)")
				try:
					rl = int(attrs[1])
				except:
					rl = 0
				length = "%i:%02i" % (int(rl // 60), rl % 60)
			self.frame.np.transfers.getFile(self.user, "\\".join([dir, file[1]]), ldir, size=file[2], bitrate=bitrate, length=length)
		if not recurse:
			return
		for directory in self.shares.keys():
			if dir in directory and dir != directory:
				self.DownloadDirectory(directory, os.path.join(ldir, ""), recurse)


	def OnDownloadFiles(self, widget, prefix = ""):
		dir = self.selected_folder
		for fn in self.selected_files:
			file = [i for i in self.shares[dir] if i[1] == fn][0]
			path = "\\".join([dir, fn])
			#size = None
			size = file[2]
			#size_l = [i[2] for i in self.shares[dir] if i[1] == fn]
			#if size_l != []: size = size_l[0]
			length = bitrate = None
			attrs = file[4]
			if attrs != []:
				bitrate = str(attrs[0])
				if attrs[2]:
					bitrate += _(" (vbr)")
				try:
					rl = int(attrs[1])
				except:
					rl = 0
				length = "%i:%02i" % (int(rl // 60), rl % 60)
			self.frame.np.transfers.getFile(self.user, path, prefix, size=size, bitrate=bitrate, length=length)

	def OnUploadDirectoryRecursiveTo(self, widget):
		self.OnUploadDirectoryTo(widget, recurse=1)
	def UploadDirectoryTo(self, user, dir, recurse = 0):
		if dir == "" or dir is None or user is None or user == "":
			return
		ldir = dir.split("\\")[-1]
		if dir in self.shares.keys():
			for file in self.shares[dir]:
				path = "\\".join([dir, file[1]])
				size = file[2]
				self.frame.np.transfers.pushFile(user, path, ldir, size=size)
				self.frame.np.transfers.checkUploadQueue()
		if not recurse:
			return
		for directory in self.shares.keys():
			if dir in directory and dir != directory:
				self.UploadDirectoryTo(user, directory, recurse)
				
	def OnUploadDirectoryTo(self, widget, recurse = 0):
		dir = self.selected_folder
		if dir is None:
			return
	
		users = []
		for entry in self.frame.np.config.sections["server"]["userlist"]:
			users.append(entry[0])
		users.sort()
		user = input_box(self.frame, title=_("Nicotine: Upload Directory's Contents"),
		message=_('Enter the User you wish to upload to:'),
		default_text='', droplist=users)
		if user is None or user == "":
			return
		self.frame.np.ProcessRequestToPeer(user, slskmessages.UploadQueueNotification(None) )
		self.UploadDirectoryTo(user, dir, recurse)
				
	def OnUploadFiles(self, widget, prefix = ""):
		dir = self.selected_folder
		users = []
		for entry in self.frame.np.config.sections["server"]["userlist"]:
			users.append(entry[0])
		users.sort()
		user = input_box(self.frame, title=_('Nicotine: Upload File(s)'),
		message=_('Enter the User you wish to upload to:'),
		default_text='', droplist=users)
		if user is None or user == "":
			pass
		else:
			self.frame.np.ProcessRequestToPeer(user, slskmessages.UploadQueueNotification(None)  )
			for fn in self.selected_files:
				self.frame.np.transfers.pushFile(user, "\\".join([dir, fn]), prefix)
				self.frame.np.transfers.checkUploadQueue()
			
	def OnPlayFiles(self, widget, prefix = ""):
		start_new_thread(self._OnPlayFiles, (widget, prefix))
	def _OnPlayFiles(self, widget, prefix = ""):
		path = self.selected_folder.replace("\\", os.sep)
		executable = self.frame.np.config.sections["players"]["default"]
		if "$" not in executable:
			return
		for fn in self.selected_files:
			file = os.sep.join([path, fn])
			if os.path.exists(file):
				executeCommand(executable, file, background=False)
		
	def OnDownloadFilesTo(self, widget):
		
		basedir, subdir = self.selected_folder.rsplit("\\", 1)
		path = os.path.join(self.frame.np.config.sections["transfers"]["downloaddir"], subdir)
		if os.path.exists(path) and os.path.isdir(path):
			ldir = ChooseDir(self.frame.MainWindow, path)
		else:
			ldir = ChooseDir(self.frame.MainWindow, self.frame.np.config.sections["transfers"]["downloaddir"])

		if ldir is None:
			return
		for directory in ldir: # iterate over selected files
			try:
				self.OnDownloadFiles(widget, directory)
			except IOError: # failed to open
				self.frame.logMessage('failed to open %r for reading', directory) # notify user

	def FindMatches(self):
		self.search_list = []
		for directory, files in self.shares.items():
			if self.query in directory.lower():
				if directory not in self.search_list:
					self.search_list.append(directory)
			for file in files:
				if self.query in file[1].lower():
					if directory not in self.search_list:
						self.search_list.append(directory)
	def OnSearch(self, widget):
		query = widget.get_text().lower()
		if self.query == query:
			self.search_position += 1
		else: 
			self.search_position = 0
			self.query = query
			if self.query == "":
				return
			self.FindMatches()

		dir = self.selected_folder
		
		if self.search_list != []:
			if self.search_position not in range(len(self.search_list)):
				self.search_position = 0
			self.search_list.sort()
			directory = self.search_list[self.search_position]
			path = self.DirStore.get_path( self.directories[directory] )
			self.FolderTreeView.expand_to_path(path)
			self.FolderTreeView.set_cursor(path)
			# Get matching files in the current directory
			resultfiles = []
			for file in self.files.keys():
				if query in file.lower():
					resultfiles.append(file)
			sel = self.FileTreeView.get_selection()
			sel.unselect_all()
			l = 1
			resultfiles.sort()
			for fn in resultfiles:
				path = self.FileStore.get_path(self.files[fn])
				# Select each matching file in directory
				sel.select_path(path)
				if l:
					# Position cursor at first match
					self.FileTreeView.scroll_to_cell(path, None, True, 0.5, 0.5)
					l = 0
		else:
			self.search_position = 0

	def OnClose(self, widget):
		self.userbrowses.remove_page(self.Main)
		del self.userbrowses.users[self.user]
		self.frame.np.ClosePeerConnection(self.conn)
		for i in self.__dict__.keys():
			del self.__dict__[i]
		
	def OnRefresh(self, widget):
		self.FolderTreeView.set_sensitive(False)
		self.FileTreeView.set_sensitive(False)
		self.SaveButton.set_sensitive(False)
		self.frame.BrowseUser(self.user)

	def OnCopyURL(self, widget):
		if self.selected_files != [] and self.selected_files != None: 
			path = "\\".join([self.selected_folder, self.selected_files[0]])
			self.frame.SetClipboardURL(self.user, path)

	def OnCopyDirURL(self, widget):
		if self.selected_folder is None:
			return
		path = self.selected_folder
		if path[:-1] != "/":
			path += "/"
		self.frame.SetClipboardURL(self.user, path)
		
	def OnFileManager(self, widget):
		if self.selected_folder is None:
			return
		path = self.selected_folder.replace("\\", os.sep)
		executable = self.frame.np.config.sections["ui"]["filemanager"]
		if "$" in executable:
			executeCommand(executable, path)
	
	def OnEncodingChanged(self, widget):
		if gtk.pygtk_version[0] >= 2 and gtk.pygtk_version[1] >= 6:
			# PyGTK 2.6
			encoding = self.Encoding.get_active_text()
		else:
			# PyGTK 2.4
			iterator = self.Encoding.get_active_iter()
			encoding_model = self.Encoding.get_model()
			encoding = encoding_model.get_value(iterator, 0)
			
		if encoding != self.encoding:
			self.encoding = encoding
			self.MakeNewModel(self.shares)
			SaveEncoding(self.frame.np, "userencoding", self.user, self.encoding)
