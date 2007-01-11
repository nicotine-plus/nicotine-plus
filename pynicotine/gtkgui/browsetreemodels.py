# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
import gtk
import gobject
import locale

from utils import FastListModel, Humanize
from pynicotine.utils import _

class DirNode:
	def __init__(self, decode, parent, name, path):
		self.decode = decode
		self.name = name
		self.parent = parent
		self.nodes = {}
		self.nodenames = []
		self.files = []
		self.model = None
		self.path = path
	
	def append(self, dirnode):
		name = dirnode.name
		self.nodes[name] = dirnode
		self.nodenames.append(name)
		self.nodenames.sort(locale.strcoll)
	
	def set_files(self, files):
		self.files = files
	
	def get_files_model(self):
		if self.model is None:
			self.model = BrowseFilesModel(self.decode, self.files)
		return self.model
		
	def __getitem__(self, i):
		try:
			return self.nodes[self.nodenames[i]]
		except IndexError:
			return None
	
	def __setitem__(self, key, value):
		if self.has_key(key):
			self.nodes[key] = value
		else:
			self.append(value)
		
	def has_key(self, name):
		return name in self.nodenames

	def keys(self):
		return self.nodenames[:]
		
	def index(self, node):
		return self.nodenames.index(node.name)
		
class BrowseDirsModel(gtk.GenericTreeModel):
	def __init__(self, decode, data):
		gtk.GenericTreeModel.__init__(self)
		
		self.decode = decode
		
		self.tree = DirNode(decode, None, "", None)
		
		for i in data.keys():
			dirs = i.split("\\")
			node = self.tree
			path = ""
			for j in dirs:
				path += j + "\\"
				if node.has_key(j):
					node = node.nodes[j]
				else:
					node[j] = DirNode(decode, node, j, path)
					node = node.nodes[j]
			node.set_files(data[i])

	def on_get_flags(self):
		return 0
	
	def on_get_n_columns(self):
		return 1
	
	def on_get_column_type(self, column):
		return gobject.TYPE_STRING
	
	def on_get_path(self, node):
		path = []
		while node.parent != None:
			path.insert(0, node.parent.index(node))
			node = node.parent
		return tuple(path)
	
	def on_get_iter(self, path):
		node = self.tree
		for i in path:
			node = node[i]
		return node
	
	def on_get_value(self, node, column):
		return node.name != "" and self.decode(node.name) or "/"
	
	def on_iter_next(self, node):
		try:
			ix = node.parent.index(node) + 1
			return node.parent[ix]
		except IndexError:
			return None
	
	def on_iter_children(self, node):
		try:
			return node[0]
		except:
			return None
	
	def on_iter_has_child(self, node):
		return len(node.keys()) > 0
	
	def on_iter_n_children(self, node):
		return len(node.keys())
	
	def on_iter_nth_child(self, node, n):
		if not node:
			node = self.tree
		try:
			return node[n]
		except:
			return None
	
	def on_iter_parent(self, node):
		return node.parent

class BrowseFilesModel(FastListModel):
	COLUMNS = 4
	COLUMN_TYPES = [gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT, gobject.TYPE_INT, gobject.TYPE_STRING]
	
	def __init__(self, decode, files):
		FastListModel.__init__(self)
		self.sort_col = -1
		self.sort_order = gtk.SORT_ASCENDING
		for file in files:
			rl = 0
			f = [decode(file[1]), Humanize(file[2])]
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
			self.data.append(f)

	def sort(self):
		col = self.sort_col
		order = self.sort_order
		if col == 1:
			col = 4
		elif col == 3:
			col = 5
		if self.COLUMN_TYPES[col] == gobject.TYPE_STRING:
			compare = locale.strcoll
		else:
			compare = cmp
			
		if order == gtk.SORT_ASCENDING:
			self.data.sort(lambda r1,r2: compare(r1[col], r2[col]))
		else:
			self.data.sort(lambda r2,r1: compare(r1[col], r2[col]))

