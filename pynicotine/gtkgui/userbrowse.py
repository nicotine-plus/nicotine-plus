# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
import gtk
import os
import urllib

from userinfo import UserTabs
from nicotine_glade import UserBrowseTab
from browsetreemodels import BrowseDirsModel, BrowseFilesModel
from utils import InitialiseColumns, PopupMenu, EncodingsMenu, SaveEncoding
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
		self.search_node = None
		self.search_text = None

		self.selected_folder = None
		self.selected_files = []
		
		self.list = {}

		self.encoding, m = EncodingsMenu(self.frame.np, "userencoding", user)
		for item in m:
			self.Encoding.append_text(item)
		if self.encoding in m:
			self.Encoding.set_active(m.index(self.encoding))
		
		renderer = gtk.CellRendererText()
		column = gtk.TreeViewColumn(_("Share tree"), renderer, text = 0)
		self.FolderTreeView.append_column(column)
		
		self.FolderTreeView.get_selection().connect("changed", self.OnSelectDir)

		cols = cols = InitialiseColumns(self.FileTreeView,
			[_("Filename"), 250, "text"],
			[_("Size"), 100, "text"],
			[_("Bitrate"), 50, "text"],
			[_("Length"), 50, "text"],
		)
		for ix in range(len(cols)):
			cols[ix].connect("clicked", self.OnResort, ix)
		
		self.FileTreeView.set_model(BrowseFilesModel(self.decode, []))
		self.FileTreeView.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

		self.FileTreeView.set_headers_clickable(True)
		self.FileTreeView.set_property("rules-hint", True)
		self.folder_popup_menu = popup = PopupMenu(self.frame)
		popup.set_user(user)
		if user == self.frame.np.config.sections["server"]["login"]:
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
				("#" + _("Get user i_nfo"), popup.OnGetUserInfo, gtk.STOCK_INFO),
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
				("#" + _("Get user i_nfo"), popup.OnGetUserInfo, gtk.STOCK_INFO),
				("#" + _("Gi_ve privileges"), popup.OnGivePrivileges, gtk.STOCK_JUMP_TO),
				("$" + _("_Add user to list"), popup.OnAddToList),
				("$" + _("_Ban this user"), popup.OnBanUser),
				("$" + _("_Ignore this user"), popup.OnIgnoreUser),
			)
		self.FolderTreeView.connect("button_press_event", self.OnFolderClicked)
		
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
				("#" + _("Get user i_nfo"), popup.OnGetUserInfo, gtk.STOCK_INFO),
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
				("#" + _("Get user i_nfo"), popup.OnGetUserInfo, gtk.STOCK_INFO),
				("#" + _("Gi_ve privileges"), popup.OnGivePrivileges, gtk.STOCK_JUMP_TO),
				("$" + _("_Add user to list"), popup.OnAddToList),
				("$" + _("_Ban this user"), popup.OnBanUser),
				("$" + _("_Ignore this user"), popup.OnIgnoreUser),
			)
		self.FileTreeView.connect("button_press_event", self.OnFileClicked)
		
	def decode(self, str):
		return self.frame.np.decode(str, self.encoding)
	
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
		for item in items[0:4]:
			item.set_sensitive(act)
		items[5].set_sensitive(act)
		if self.user == self.frame.np.config.sections["server"]["login"]:
			items[10].set_active(self.user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
			items[11].set_active(self.user in self.frame.np.config.sections["server"]["banlist"])
			items[12].set_active(self.user in self.frame.np.config.sections["server"]["ignorelist"])
		else:
			items[11].set_active(self.user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
			items[12].set_active(self.user in self.frame.np.config.sections["server"]["banlist"])
			items[13].set_active(self.user in self.frame.np.config.sections["server"]["ignorelist"])
		
		self.folder_popup_menu.popup(None, None, None, event.button, event.time)
	
	def SelectedFilesCallback(self, model, path, iter):
		self.selected_files.append(model.data[path[0]][6])
	
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
		
		# daelstorm modified the numbers for the upload menu item
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
		self.list = list
		self.selected_folder = None
		self.selected_files = []
		self.FileTreeView.set_model(BrowseFilesModel(self.decode, []))
		model = BrowseDirsModel(self.decode, list)
		self.FolderTreeView.set_model(model)
		self.FolderTreeView.set_sensitive( True)
		
	def ShowInfo(self, msg):
		self.conn = None
		self.MakeNewModel(msg.list)

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
			self.FileTreeView.set_model(BrowseFilesModel(self.decode, []))
			return
		path = model.get_path(iter)
		node = model.tree
		for i in path:
			node = node[i]
		self.selected_folder = node
		self.FileTreeView.set_model(node.get_files_model())

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
		self.DownloadDirectory(self.selected_folder, "", 1)
	
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

	
	def DownloadDirectory(self, node, prefix = "", recurse = 0):
		if node == None:
			return
		dir = node.path
		ldir = prefix + dir[:-1].split("\\")[-1]
		for file in node.files:
			self.frame.np.transfers.getFile(self.user, dir + file[1], ldir)
		if not recurse:
			return
		for n in node.nodes.values():
			self.DownloadDirectory(n, os.path.join(ldir, ""), recurse)

	def OnDownloadFiles(self, widget, prefix = ""):
		dir = self.selected_folder.path
		for fn in self.selected_files:
			self.frame.np.transfers.getFile(self.user, dir + fn, prefix)

	# Here daelstorm adds the upload command
	def OnUploadFiles(self, widget, prefix = ""):
		dir = self.selected_folder.path

		user = input_box(self.frame, title='Nicotine: Remote Upload File(s)',
		message='Enter the User you wish to upload to:',
		default_text='')
		if user is None:
			pass
		else:
                        self.frame.np.ProcessRequestToPeer(user,slskmessages.UploadQueueNotification(None)  )
			for fn in self.selected_files:
				self.frame.np.transfers.pushFile(user, dir + fn, prefix)
				self.frame.np.transfers.checkUploadQueue()
			
	def OnPlayFiles(self, widget, prefix = ""):
		dir = self.selected_folder.path

		direct = dir.replace("\\", "/")
		for fn in self.selected_files:
			os.system("%s \"%s%s\" &" %(self.frame.np.config.sections["players"]["default"], direct, fn ) )
				
			
			
	def OnDownloadFilesTo(self, widget):
		ldir = ChooseDir(self.frame.MainWindow, self.frame.np.config.sections["transfers"]["downloaddir"])
		if ldir is None:
			return

		for directory in ldir: # iterate over selected files
			try:
 				self.OnDownloadFiles(widget, directory)
				
			except IOError: # failed to open
				self.message('failed to open %r for reading', directory) # notify user

	def OnSearch(self, widget):
		text = widget.get_text().lower()
		if not text:
			return
		
		model = self.FolderTreeView.get_model()
		if model is None:
			return
		
		if text != self.search_text or self.search_node is None:
			self.search_node = model.tree
			self.search_text = text
		
		self.search_node, resultfiles = self.FindNode(self.search_node, text, False)
		if self.search_node is not None:
			path = model.on_get_path(self.search_node)
			for i in range(1, len(path)):
				self.FolderTreeView.expand_row(path[:i], False)
			iter = model.get_iter(path)
			sel = self.FolderTreeView.get_selection()
			sel.unselect_all()
			sel.select_path(path)
			self.FolderTreeView.scroll_to_cell(path, None, True, 0.5, 0.5)
			
			sel = self.FileTreeView.get_selection()
			fmodel = self.FileTreeView.get_model()
			sel.unselect_all()
			filetable = [f[6] for f in fmodel.data]
			for fn in resultfiles:
				ix = filetable.index(fn)
				sel.select_path((ix,))
		
	def FindNode(self, node, text, allowed = True, allow_parent = True):
		if node is None:
			return None, []
		
		if allowed:
			returnfiles = []
			match = False
			if node.name.lower().find(text) > -1:
				match = True
			for row in node.files:
				if row[1].lower().find(text) > -1:
					match = True
					returnfiles.append(row[1])
			if match:
				return node, returnfiles
		if node.nodenames:
			subnode = node.nodes[node.nodenames[0]]
			ix = 0
		else:
			subnode = None
		while subnode:
			matchnode, returnfiles = self.FindNode(subnode, text, True, False)
			if matchnode is not None:
				return matchnode, returnfiles
			ix += 1
			if ix == len(node.nodes):
				subnode = None
			else:
				subnode = node.nodes[node.nodenames[ix]]
		
		if not allow_parent:
			return None, []
		
		
		parent = node.parent
		while parent:
			ix = parent.nodenames.index(node.name)
			ix += 1
			if ix == len(parent.nodenames):
				node = parent
				parent = node.parent
				continue

			for subnodename in parent.nodenames[ix:]:
				subnode = parent.nodes[subnodename]
				matchnode, resultfiles = self.FindNode(subnode, text, True, False)
				if matchnode is not None:
					return matchnode, resultfiles
			node = parent
			parent = node.parent
		return None, []

	def OnClose(self, widget):
		self.userbrowses.remove_page(self.Main)
		del self.userbrowses.users[self.user]
		self.Main.destroy()

	def OnRefresh(self, widget):
		self.FolderTreeView.set_sensitive( False)
		self.frame.BrowseUser(self.user)

	def OnCopyURL(self, widget):
		if self.selected_files != [] and self.selected_files != None: 
			path = self.selected_folder.path + self.selected_files[0]
			self.frame.SetClipboardURL(self.user, path)

	def OnCopyDirURL(self, widget):
		path = self.selected_folder.path
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
			self.MakeNewModel(self.list)
			SaveEncoding(self.frame.np, "userencoding", self.user, self.encoding)
