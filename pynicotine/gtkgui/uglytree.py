# Copyright (C) 2007 Nick Voronin. All rights reserved.
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

import gtk

class UglyTree(gtk.GenericTreeModel):
	'''This class represents the model of a tree.  The iterators used
	to represent positions are converted to python objects when passed
	to the on_* methods.  This means you can use any python object to
	represent a node in the tree.  The None object represents a NULL
	iterator.'''

	def __init__(self, types, list=[]):
		'''constructor for the model.  Make sure you call
		PyTreeModel.__init__'''
		gtk.GenericTreeModel.__init__(self)
		self.types = types
		self.MakeTree(list)

	def MakeTree(self, list):
		'''input:  [(full path, data), ...]
		   output: ([(dir name, parent, data), ...], [(nchildren, firstchild), ...])'''
		# Keep these local for improved speeds
		def _insensitivesort(x):
			if x[0][-1] != dirseparator:
				return (x[0]+dirseparator).lower()
			return x[0].lower()
		def _sensitivesort(x):
			if x[0][-1] != dirseparator:
				return x[0]+dirseparator
			return x[0]
		dirseparator = '\\'
		# I need this hack to sort items so 'dir1' will be after 'dir1 bis' and 
		# right before 'dir1\\dir2', emulating proper depth-first tree traversal
		# The fact that there are dirs like 'C:\\' which already have trailing slash 
		# should be taken into account as well
		if len(list) > 0:
			top = list[0][0].split(dirseparator)[0]
			if len(top) == 2 and top[1] == ':':
				# for path in form x:\\... assume win32 platform and make case insensitive sort
				list.sort(key=_insensitivesort)
			else:
				# case sensitive sort looks very unnatural for me, but it's important for proper tree traversal
				# in case there are directories which names differ only in case.
				# Maybe I can do additional sorting of formed tree later
				list.sort(key=_sensitivesort)
		#list.sort(key=lambda x: x[0].split(dirseparator))
		empty = []
		old_s = []
		old_l = 0
		self.tree1 = [[('', -1, empty)]] # immutable lists
		self.tree2 = [[(0, None)]] # mutable lists
		for item in list:
			#print '%s : %s' % (item[0], item[1])
			level = 0
			s = item[0].split(dirseparator)
			l = len(s)
			# Special case for trailing \, esp. X:\
			if s[-1] == '':
				l -= 1
			end = min(l, old_l)
			while l >= len(self.tree1):
				self.tree1.append([])
				self.tree2.append([])
			
			# skip through already added dirs in path
			while level < end and s[level] == old_s[level]:
				level += 1
			while level < l:
				if(level == l-1):
					self.tree1[level+1].append( (s[level], len(self.tree1[level])-1, item[1]) )
				else:
					self.tree1[level+1].append( (s[level], len(self.tree1[level])-1, empty) )
				self.tree2[level+1].append( (0, None) )

				p_nchildren, p_firstchild = self.tree2[level][-1]
				p_nchildren += 1
				if p_firstchild == None: # parent had no childs
					p_firstchild = len(self.tree1[level+1])-1
				self.tree2[level][-1] = (p_nchildren, p_firstchild)
				level += 1
			old_s = s
			old_l = l

#For iterators:
#None is equivalent to (0,0) in internal structure
#(0,0) should not be normally passed to handlers
#(0,0) is not returned to the caller, None is returned instead

	def GetValue(self, node):
		#print "GetValue(self, node):"
		level, number = node
		return self.tree1[level][number][0]
	def GetData(self, node):
		#print "GetData(self, node):"
		level, number = node
		return self.tree1[level][number][2]
	def GetPathString(self, path):
		assert isinstance(path, tuple)
		level = 1
		offset = 0
		dirs = []
		for n in path:
			dirs.append(self.tree1[level][offset+n][0])
			offset = self.tree2[level][offset+n][1] #firstchild
			level += 1
		return '\\'.join(dirs)

	def FindMatches(self, query):
	# Completely un-generic. I know, I know. One should make tree iterable, 
	# or add some generic traversing method... Do it. :)
		search_list = []
		level = 1
		while level < len(self.tree1):
			offset = 0
			while offset < len(self.tree1[level]):
				directory, parent, files = self.tree1[level][offset]
				if query in directory.lower():
					search_list.append(self.on_get_path((level, offset)))
				else:
					if files != None:
						for file in files:
							if query in file[1].lower():
								search_list.append(self.on_get_path((level, offset)))
								break
				offset += 1
			level += 1
		search_list.sort()
		return search_list

	def GetParent(self, node):
		#print "GetParent(self, node):"
		level, number = node
		if level <= 1:
			return None
		return (level-1, self.tree1[level][number][1])
	def GetChild(self, node):
		#print "GetChild(self, node):"
		if node == None:
			node = (0,0)
		level, number = node
		if self.tree2[level][number][0] == 0:
			return None
		return (level+1, self.tree2[level][number][1])
	def GetChildren(self, node):
		#print "GetChildren(self, node):"
		if node == None:
			node = (0,0)
		level, number = node
		nchildren, firstchild = self.tree2[level][number]
		#print "level=%s, nchildren=%s, firstchild=%s" % (level, nchildren, firstchild)
		return (nchildren, (level+1, firstchild))
	def GetNext(self, node):
		#print "GetNext(self, node=%s):" % (node,)
		if node != None and node[0] > 0:
			nchildren, (level, first_node) = self.GetChildren(self.GetParent(node))
			level, number = node
			if number + 1 >= first_node + nchildren: # last node at level
				return None
			return (level, number+1)
	def GetOffset(self, node):
		#print "GetOffset(self, node=%s):" % (node,)
		assert node != None and node[0] > 0
		level, number = node
		p_level, p_number = self.GetChild(self.GetParent(node))
		return number - p_number

	# the implementations for TreeModel methods
	def on_get_flags(self):
		'''returns the GtkTreeModelFlags for this particular type of model'''
		#print "on_get_flags(self):"
		return gtk.TREE_MODEL_ITERS_PERSIST
	def on_get_n_columns(self):
		'''returns the number of columns in the model'''
		#print "on_get_n_columns(self):"
		return 1
	def on_get_column_type(self, index):
		'''returns the type of a column in the model'''
		#print "on_get_column_type(self, index):"
		return self.types[index]
	def on_get_path(self, node):
		'''returns the tree path (a tuple of indices at the various
		levels) for a particular node.'''
		#print "on_get_path(self, %s):" % (node,)
		if node == None:
			return ()
		path = (self.GetOffset(node),)
		while node[0] > 1:
			node = self.GetParent(node)
			path = (self.GetOffset(node),) + path
		return path
	def on_get_iter(self, path):
		'''returns the node corresponding to the given path.'''
		#print "on_get_iter(self, %s):" % (path,)
		node = None
		for i in path:
			#try:
				returnvalue = self.GetChild(node)
				if returnvalue:
					level, number = self.GetChild(node)
					node = (level, number + i)
			#except TypeError, e:
			#	print 'TypeError in on_get_iter for path %s: %s' % (path, str(e))
			#	node = None
		return node
	def on_get_value(self, node, column):
		'''returns the value stored in a particular column for the node'''
		#print "on_get_value(self, node, column):"
		assert column == 0
		return self.GetValue(node)
	def on_iter_next(self, node):
		'''returns the next node at this level of the tree'''
		#print "on_iter_next(self, node):"
		assert node != None and node[0] > 0
		return self.GetNext(node)
	def on_iter_children(self, node):
		'''returns the first child of this node'''
		#print "on_iter_children(self, node):"
		return self.GetChild(node)
	def on_iter_has_child(self, node):
		'''returns true if this node has children'''
		#print "on_iter_has_child(self, node):"
		nchildren, nnode = self.GetChildren(node)
		return nchildren > 0
	def on_iter_n_children(self, node):
		'''returns the number of children of this node'''
		#print "on_iter_n_children(self, %s):" % (node,)
		nchildren, nnode = self.GetChildren(node)
		return nchildren
	def on_iter_nth_child(self, node, n):
		'''returns the nth child of this node'''
		#print "on_iter_nth_child(self, node=%s, n=%d):" % (node, n)
		nchildren, (level, number) = self.GetChildren(node)
		if nchildren <= n:
			return None
		return (level, number + n)
	def on_iter_parent(self, node):
		'''returns the parent of this node'''
		#print "on_iter_parent(self, node):"
		assert node != None and node[0] > 0
		return self.GetParent(node)
	# the implementatinos for TreeStore
	##def append(self, parent, row = None):
	##	pass
	### the implementations for TreeModel
	##def get_path(self, iter):
	##	pass
	### the implementations for TreeSortable methods
	##def sort_column_changed(self):
	##	pass
	##def get_sort_column_id(self):
	##	return 0
	##def set_sort_column_id(self, sort_column_id, order):
	##	pass
	##def set_sort_func(self, sort_column_id, sort_func, user_data=None):
	##	pass
	##def set_default_sort_func(self, sort_func, user_data=None):
	##	pass
	##def has_default_sort_func(self):
	##	return True
