# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
import gtk
import os, sys
import urllib
import gobject
import gc
from userinfo import UserTabs
from nicotine_glade import UserBrowseTab

from utils import InitialiseColumns, PopupMenu, EncodingsMenu, SaveEncoding, Humanize
from dirchooser import ChooseDir
from entrydialog import *
from pynicotine import slskmessages

from pynicotine.utils import _

class UserBrowse(UserBrowseTab):
	def __init__(self, userbrowses, user, conn):

		UserBrowseTab.__init__(self, False)
		
		self.userbrowses = userbrowses
		self.userbrowses.set_tab_pos(gtk.POS_TOP)
		self.frame = userbrowses.frame
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
			
		self.encoding, m = EncodingsMenu(self.frame.np, "userencoding", user)
		
		self.EncodingStore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
		self.Encoding.set_size_request(100, -1)
		self.Encoding.set_model(self.EncodingStore)
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
		# GTK 2.10 
		try: self.FolderTreeView.set_property("enable-tree-lines", True)
		except: pass

		
		cols = InitialiseColumns(self.FolderTreeView,
			[_("Directories"), -1, "text"], #0
		)
		cols[0].set_sort_column_id(0)
		self.folder_popup_menu = popup = PopupMenu(self.frame)
		popup.set_user(user)
		if user == self.frame.np.config.sections["server"]["login"]:
			popup.setup(
				("#" + _("_Download directory"), self.OnDownloadDirectory, gtk.STOCK_GO_DOWN),
				("#" + _("Download directory _to..."), self.OnDownloadDirectoryTo, gtk.STOCK_GO_DOWN),
				("#" + _("Download _recursive"), self.OnDownloadDirectoryRecursive, gtk.STOCK_GO_DOWN),
				("#" + _("Download r_ecursive to..."), self.OnDownloadDirectoryRecursiveTo, gtk.STOCK_GO_DOWN),
				("#" + _("Upload Directory to..."), self.OnUploadDirectoryTo, gtk.STOCK_GO_UP),
				("#" + _("Upload Directory recursive to..."), self.OnUploadDirectoryRecursiveTo, gtk.STOCK_GO_UP),
				("", None),
				("#" + _("Copy _URL"), self.OnCopyDirURL, gtk.STOCK_COPY),
				("", None),
				("#" + _("Send _message"), popup.OnSendMessage, gtk.STOCK_EDIT),
				("#" + _("Show IP a_ddress"), popup.OnShowIPaddress, gtk.STOCK_NETWORK),
				("#" + _("Get user i_nfo"), popup.OnGetUserInfo, gtk.STOCK_DIALOG_INFO),
				("$" + _("_Add user to list"), popup.OnAddToList),
				("$" + _("_Ban this user"), popup.OnBanUser),
				("$" + _("_Ignore this user"), popup.OnIgnoreUser),
			)
		else:
			popup.setup(
				("#" + _("_Download directory"), self.OnDownloadDirectory, gtk.STOCK_GO_DOWN),
				("#" + _("Download directory _to..."), self.OnDownloadDirectoryTo, gtk.STOCK_GO_DOWN),
				("#" + _("Download _recursive"), self.OnDownloadDirectoryRecursive, gtk.STOCK_GO_DOWN),
				("#" + _("Download r_ecursive to..."), self.OnDownloadDirectoryRecursiveTo, gtk.STOCK_GO_DOWN),
				("", None),
				("#" + _("Copy _URL"), self.OnCopyDirURL, gtk.STOCK_COPY),
				("", None),
				("#" + _("Send _message"), popup.OnSendMessage, gtk.STOCK_EDIT),
				("#" + _("Show IP a_ddress"), popup.OnShowIPaddress, gtk.STOCK_NETWORK),
				("#" + _("Get user i_nfo"), popup.OnGetUserInfo, gtk.STOCK_DIALOG_INFO),
				("#" + _("Gi_ve privileges"), popup.OnGivePrivileges, gtk.STOCK_JUMP_TO),
				("$" + _("_Add user to list"), popup.OnAddToList),
				("$" + _("_Ban this user"), popup.OnBanUser),
				("$" + _("_Ignore this user"), popup.OnIgnoreUser),
			)
		self.FolderTreeView.connect("button_press_event", self.OnFolderClicked)
		self.FolderTreeView.get_selection().connect("changed", self.OnSelectDir)
		
		# DecodedFilename, HSize, Bitrate, HLength, Size, Length, RawFilename
		self.FileStore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT, gobject.TYPE_INT, gobject.TYPE_STRING)
		self.FileTreeView.set_model(self.FileStore)
		cols = InitialiseColumns(self.FileTreeView,
			[_("Filename"), 250, "text"],
			[_("Size"), 100, "text"],
			[_("Bitrate"), 50, "text"],
			[_("Length"), 50, "text"],
		)
		cols[0].set_sort_column_id(0)
		cols[1].set_sort_column_id(4)
		cols[2].set_sort_column_id(2)
		cols[3].set_sort_column_id(5)

		self.FileTreeView.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

		self.FileTreeView.set_headers_clickable(True)
		self.FileTreeView.set_property("rules-hint", True)
		
		self.file_popup_menu = popup = PopupMenu(self.frame)
		popup.set_user(user)
		if user == self.frame.np.config.sections["server"]["login"]:
			popup.setup(
				("#" + _("_Download file(s)"), self.OnDownloadFiles, gtk.STOCK_GO_DOWN),
				("#" + _("Download _to..."), self.OnDownloadFilesTo, gtk.STOCK_GO_DOWN),
				("", None),
				("#" + _("Copy _URL"), self.OnCopyURL, gtk.STOCK_COPY),
				("", None),
				("#" + _("Up_load file(s)"), self.OnUploadFiles, gtk.STOCK_GO_UP),
				("#" + _("Send to _player"), self.OnPlayFiles, gtk.STOCK_MEDIA_PLAY),
				("#" + _("Send _message"), popup.OnSendMessage, gtk.STOCK_EDIT),
				("#" + _("Show IP a_ddress"), popup.OnShowIPaddress, gtk.STOCK_NETWORK),
				("#" + _("Get user i_nfo"), popup.OnGetUserInfo, gtk.STOCK_DIALOG_INFO),
				("$" + _("_Add user to list"), popup.OnAddToList),
				("$" + _("_Ban this user"), popup.OnBanUser),
				("$" + _("_Ignore this user"), popup.OnIgnoreUser),
			)
		else:
			popup.setup(
				("#" + _("_Download file(s)"), self.OnDownloadFiles, gtk.STOCK_GO_DOWN),
				("#" + _("Download _to..."), self.OnDownloadFilesTo, gtk.STOCK_GO_DOWN),
				("", None),
				("#" + _("Copy _URL"), self.OnCopyURL, gtk.STOCK_COPY),
				("", None),
				("#" + _("Send _message"), popup.OnSendMessage, gtk.STOCK_EDIT),
				("#" + _("Show IP a_ddress"), popup.OnShowIPaddress, gtk.STOCK_NETWORK),
				("#" + _("Get user i_nfo"), popup.OnGetUserInfo, gtk.STOCK_DIALOG_INFO),
				("#" + _("Gi_ve privileges"), popup.OnGivePrivileges, gtk.STOCK_JUMP_TO),
				("$" + _("_Add user to list"), popup.OnAddToList),
				("$" + _("_Ban this user"), popup.OnBanUser),
				("$" + _("_Ignore this user"), popup.OnIgnoreUser),
			)
		self.FileTreeView.connect("button_press_event", self.OnFileClicked)
		
	def decode(self, str):
		return self.frame.np.decode(str, self.encoding)
	
	def OnExpand(self, widget):
		if self.ExpandButton.get_active():
			self.FolderTreeView.expand_all()
		else:
			self.FolderTreeView.collapse_all()
			
			dirs = self.directories.keys()
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
		for item in items[0:6]:
			item.set_sensitive(act)
		
		if self.user == self.frame.np.config.sections["server"]["login"]:
			items[6].set_sensitive(act)
			items[7].set_sensitive(act)
			items[12].set_active(self.user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
			items[13].set_active(self.user in self.frame.np.config.sections["server"]["banlist"])
			items[14].set_active(self.user in self.frame.np.config.sections["server"]["ignorelist"])
		else:
			items[11].set_active(self.user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
			items[12].set_active(self.user in self.frame.np.config.sections["server"]["banlist"])
			items[13].set_active(self.user in self.frame.np.config.sections["server"]["ignorelist"])
		
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
		
		act = True
		if not self.selected_files:
			act = False
		items = self.file_popup_menu.get_children()
		items[0].set_sensitive(act)
		items[1].set_sensitive(act)
		items[3].set_sensitive(act)
		if len(self.selected_files) == 1:
			items[3].set_sensitive(True)
		else:
			items[3].set_sensitive(False)
		
		if self.user == self.frame.np.config.sections["server"]["login"]:
			if len(self.selected_files) >= 1:
				items[5].set_sensitive(True)
			else:
				items[5].set_sensitive(False)
			items[10].set_active(self.user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
			items[11].set_active(self.user in self.frame.np.config.sections["server"]["banlist"])
			items[12].set_active(self.user in self.frame.np.config.sections["server"]["ignorelist"])
		else:
			items[9].set_active(self.user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
			items[10].set_active(self.user in self.frame.np.config.sections["server"]["banlist"])
			items[11].set_active(self.user in self.frame.np.config.sections["server"]["ignorelist"])
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
	
		self.SetDirectory(self.BrowseGetDirs())
		self.FolderTreeView.set_sensitive(True)
		self.FileTreeView.set_sensitive(True)
		self.SaveButton.set_sensitive(True)
		self.RefreshButton.set_sensitive(True)
		
		if self.ExpandButton.get_active():
			self.FolderTreeView.expand_all()
		else:
			self.FolderTreeView.collapse_all()
		
	def BrowseGetDirs(self):
		sorted = []
		for dirs in self.shares.keys():
			sorted.append(dirs)
		sorted.sort()
		children = []
		directory = ""
		self.directories = {}
		if sorted != []:
			for item in sorted:
				s = item.split("\\")
				path = ''

				parent = s[0]
				if parent == '':
					parent += "\\"
					if parent not in self.directories.keys():
						self.directories[parent] =  self.DirStore.append(None, [parent, parent])
				parent = s[0]
				for seq in s[1:]:
					if parent == "":
						parent += "\\"
						path = parent+seq
					else:
						path = parent+"\\"+seq
					

					if parent not in self.directories.keys():
						self.directories[parent] =  self.DirStore.append(None, [parent, parent])
					

					if path not in children:
						children.append(path)
						self.directories[path] = self.DirStore.append(self.directories[parent], [path.split("\\")[-1], path ] )
					parent = path

			directory = children[0]
		return directory
	
			
	def SetDirectory(self, directory):
		self.selected_folder = directory
		self.FileStore.clear()
		self.files.clear()
		if not self.shares.has_key(directory):
			return
		
		path = self.DirStore.get_path( self.directories[directory] )
		

		files = self.shares[directory]
		for file in files:
			
			rl = 0
			f = [self.decode(file[1]), Humanize(file[2])]
			if file[3] == "mp3":
				attrs = file[4]
				if len(attrs) >= 3:
					br = str(attrs[0])
					if attrs[2]:
						br = br + _(" (vbr)")
					l = "%i:%02i" % (attrs[1] / 60, attrs[1] % 60)
					rl = attrs[1]
					f += [br, l]
				else:
					f += ["", ""]
			elif file[3] == "":
				f += ["", ""]
			else:
				f += [file[4], file[4]]
			f += [file[2], rl, file[1]]
		
			self.files[f[0]] = self.FileStore.append(f)
		
			
	def OnSave(self, widget):
		configdir, config = os.path.split(self.frame.np.config.filename)
		sharesdir = os.path.abspath(configdir+os.sep+"usershares"+os.sep)
			
		try:
			if not os.path.exists(sharesdir):
				os.mkdir(sharesdir)
		except Exception, msg:
			error = _("Can't create directory '%s', reported error: %s" % (sharesdir, msg))
			print error
			self.frame.logMessage(error)
		try:
			import pickle
			import bz2
			sharesfile = bz2.BZ2File(os.path.join(sharesdir, self.encode(self.user)), 'w' )
			pickle.dump(self.shares, sharesfile)
			sharesfile.close()
		except Exception, msg:
			error = _("Can't save shares, '%s', reported error: %s" % (self.user, msg) )
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
			go_ahead = Option_Box(self.frame, title=_('Nicotine+: Download %i files?' %numfiles), message=_("Are you sure you wish to download %i files from %s's directory %s?" %( numfiles, self.user, dir ) ), option1=_("Ok"), option3=_("Cancel"), option2=None, status="warning" )
			
		else:
			go_ahead = 1
			
		if go_ahead == 1:
			# Good to go, we download these
			for item in files:
				file, localpath = item
				self.frame.np.transfers.getFile(self.user, file, localpath)
			
	def DownloadDirectoryRecursive(self, dir, prefix = ""):
		# Find all files and add them to list
		if dir == None:
			return
		localdir = prefix + dir.split("\\")[-1]

		files = []
		if dir in self.shares.keys():
			for file in self.shares[dir]:
				files.append(["\\".join([dir, file[1]]), localdir])
		
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
				self.message('failed to open %r for reading', directory) # notify user

	def OnDownloadDirectoryRecursiveTo(self, widget):
		dir = ChooseDir(self.frame.MainWindow, self.frame.np.config.sections["transfers"]["downloaddir"])
		if dir is None:
			return
		for directory in dir: # iterate over selected files
			try:
 				
				self.DownloadDirectory(self.selected_folder, os.path.join(directory, ""), 1)
				
			except IOError: # failed to open
				self.message('failed to open %r for reading', directory) # notify user

	
	def DownloadDirectory(self, dir, prefix = "", recurse = 0):
		if dir == None:
			return
		ldir = prefix + dir.split("\\")[-1]
		for file in self.shares[dir]:
			self.frame.np.transfers.getFile(self.user, "\\".join([dir, file[1]]), ldir)
		if not recurse:
			return
		for directory in self.shares.keys():
			if dir in directory and dir != directory:
	
				self.DownloadDirectory(directory, os.path.join(ldir, ""), recurse)


	def OnDownloadFiles(self, widget, prefix = ""):
		dir = self.selected_folder
		for fn in self.selected_files:
			self.frame.np.transfers.getFile(self.user, "\\".join([dir, fn]), prefix)

	
	def OnUploadDirectoryRecursiveTo(self, widget):
		self.OnUploadDirectoryTo(widget, recurse=1)
	
	def UploadDirectoryTo(self, user, dir, recurse = 0):
		if dir == None:
			return

		ldir = dir[:-1].split("\\")[-1]
		
		if user is None or user == "":
			return
		else:
			if dir in self.shares.keys():

				for file in self.shares[dir]:
					self.frame.np.transfers.pushFile(user, "\\".join([dir, file[1]]), ldir)
					self.frame.np.transfers.checkUploadQueue()
		if not recurse:
			return

		for directory in self.shares.keys():
			if dir in directory and dir != directory:
				self.UploadDirectoryTo(user, directory, recurse)
				
	def OnUploadDirectoryTo(self, widget, recurse = 0):
		dir = self.selected_folder
		if dir == None:
			return
	
		users = []
		for entry in self.frame.np.config.sections["server"]["userlist"]:
			users.append(entry[0])
		users.sort()
		user = input_box(self.frame, title=_("Nicotine: Upload Directory's Contents"),
		message=_('Enter the User you wish to upload to:'),
		default_text='', droplist=users)
		self.frame.np.ProcessRequestToPeer(user,slskmessages.UploadQueueNotification(None) )
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
			self.frame.np.ProcessRequestToPeer(user,slskmessages.UploadQueueNotification(None)  )
			for fn in self.selected_files:
				self.frame.np.transfers.pushFile(user, "\\".join([dir, fn]), prefix)
				self.frame.np.transfers.checkUploadQueue()
			
	def OnPlayFiles(self, widget, prefix = ""):
		dir = self.selected_folder
		
		direct = dir.replace("\\", os.sep)
		for fn in self.selected_files:
			os.system("%s \"%s\" &" %(self.frame.np.config.sections["players"]["default"], os.path.join(direct, fn) ) )

			
			
	def OnDownloadFilesTo(self, widget):
		ldir = ChooseDir(self.frame.MainWindow, self.frame.np.config.sections["transfers"]["downloaddir"])
		if ldir is None:
			return

		for directory in ldir: # iterate over selected files
			try:
 				self.OnDownloadFiles(widget, directory)
				
			except IOError: # failed to open
				self.message('failed to open %r for reading', directory) # notify user

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
		


	def OnRefresh(self, widget):
		self.FolderTreeView.set_sensitive(False)
		self.FileTreeView.set_sensitive(False)
		self.SaveButton.set_sensitive(False)
		self.RefreshButton.set_sensitive(False)
		self.frame.BrowseUser(self.user)

	def OnCopyURL(self, widget):
		if self.selected_files != [] and self.selected_files != None: 
			path = "\\".join([self.selected_folder, self.selected_files[0]])
			self.frame.SetClipboardURL(self.user, path)

	def OnCopyDirURL(self, widget):
		path = self.selected_folder
		self.frame.SetClipboardURL(self.user, path)

	def OnEncodingChanged(self, widget):
		try:
			# PyGTK 2.6
			encoding = self.Encoding.get_active_text()
		except:
			# PyGTK 2.4
			iter = self.Encoding.get_active_iter()
			encoding_model = self.Encoding.get_model()
			encoding = encoding_model.get_value(iter, 0)
		if encoding != self.encoding:
			self.encoding = encoding
			self.MakeNewModel(self.shares)
			SaveEncoding(self.frame.np, "userencoding", self.user, self.encoding)
