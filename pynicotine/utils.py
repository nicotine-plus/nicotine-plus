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
# Based on code from Nicotine, previous copyright below:
# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
# Based on code from PySoulSeek, original copyright note:
# Copyright (c) 2001-2003 Alexander Kanavin. All rights reserved

"""
This module contains utility fuctions.
"""

version = "1.2.11svn"
latesturl = "http://nicotine-plus.sourceforge.net/LATEST"

import string
from UserDict import UserDict
import os, dircache
import sys
import gobject
win32 = sys.platform.startswith("win")
frame = 0
log = 0
language = ""
try:
	import mp3_mutagen as mp3
except ImportError:
	print "Failed to import the Mutagen library, falling back to old library. To improve meta data please install Mutagen."
	import mp3

try:
	import ogg.vorbis
	vorbis = ogg.vorbis
except:
	try:
		import _vorbis
		vorbis = _vorbis
	except:
		vorbis = None

import gettext
tr_cache = {}



def ChangeTranslation(lang):
	global language
	global tr_cache
	global langTranslation
	language = lang
	message = ""
	if language == "":
		langTranslation = gettext
		return
	try:
		langTranslation = gettext.translation('nicotine', languages=[language])
		langTranslation.install()
	except IOError, e:
		message = _("Translation not found for '%s': %s") % (language, e)
		langTranslation = gettext
	except IndexError, e:
		message = _("Translation was corrupted for '%s': %s") % (language, e)
		langTranslation = gettext
	else:
		# We need to force LC_ALL env variable to get buttons translated as well
		# On Windows we can't use os.environ, see pynicotine/libi18n.py
		if win32:
			import libi18n
			libi18n._putenv('LC_ALL',language)
			del libi18n
		# The Unix part is quite funny too...
		else:
			import locale
			# Let's try to force the locale with the right lang
			# locale.normalize will return bla_BLA.USUAL_ENCODINGS, so we first want to try to use unicode
			try:
				locale.setlocale(locale.LC_ALL, locale.normalize(language).split('.')[0]+'.UTF-8')
			except locale.Error, e:
				# If it fails we'll trust normalize() and use its encoding
				try:
					locale.setlocale(locale.LC_ALL, locale.normalize(language))
				# Sorry, please generate the right locales
				except locale.Error, e:
					message = _("Force lang failed: '%s' (%s and %s tested)" ) % (e, locale.normalize(language).split('.')[0]+'.UTF-8', locale.normalize(language))
			del locale
	return message
ChangeTranslation(language)
# Translation Function
def _(s):
	global tr_cache
	global langTranslation
	# Don't translate empty strings
	# Poedit uses empty strings as metadata
	if s == "": return s
	if s not in tr_cache:
		tr_cache[s] = langTranslation.gettext(s)
	return tr_cache[s]

def getServerList(url):
	""" Parse server text file from http://www.slsk.org and 
	return a list of servers """
	import urllib, string
	try:
		f = urllib.urlopen(url)
		list = [string.strip(i) for i in f.readlines()]
	except:
		return []
	try:
		list = list[list.index("--servers")+1:]
	except:
		return []
	list = [string.split(i,":",2) for i in list]
	try:
		return [[i[0],i[2]]  for i in list]
	except:
		return []

# Rescan directories in shared databases
def rescandirs(shared_directories, oldmtimes, oldfiles, sharedfilesstreams, yieldfunction, progress=None, name="", rebuild=False):
	"""
	Check for modified or new files via OS's last mtime on a directory,
	or, if rebuild is True, all directories
	"""
	#returns dict in format:  { Directory : mtime, ... }
	
	gobject.idle_add(progress.set_text, _("Checking for changes"))
	gobject.idle_add(progress.show)
	gobject.idle_add(progress.set_fraction, 0)

	if win32:
		newmtimes = getDirsMtimesUnicode(shared_directories, yieldfunction)
	else:
		newmtimes = getDirsMtimes(shared_directories, yieldfunction)
	gobject.idle_add(progress.set_text, _("Scanning %s") % name)
	# Get list of files
	# returns dict in format { Directory : { File : metadata, ... }, ... }
	if win32:
		newsharedfiles = getFilesListUnicode(newmtimes, oldmtimes, oldfiles, yieldfunction, progress, rebuild)
	else:
		newsharedfiles = getFilesList(newmtimes, oldmtimes, oldfiles, yieldfunction, progress, rebuild)
	# Pack shares data
	# returns dict in format { Directory : hex string of files+metadata, ... }
	gobject.idle_add(progress.set_text, _("Building DataBase"))
	newsharedfilesstreams = getFilesStreams(newmtimes, oldmtimes, sharedfilesstreams, newsharedfiles, yieldfunction)
	
	# Update Search Index
	# newwordindex is a dict in format {word: [num, num, ..], ... } with num matching
	# keys in newfileindex
	# newfileindex is a dict in format { num: (path, size, (bitrate, vbr), length), ... }
	gobject.idle_add(progress.set_text, _("Building Index"))
	newwordindex, newfileindex = getFilesIndex(newmtimes, oldmtimes, shared_directories, newsharedfiles, yieldfunction)
	gobject.idle_add(progress.set_fraction, 1.0)

	return newsharedfiles, newsharedfilesstreams, newwordindex, newfileindex, newmtimes
    

# Get Modification Times
def getDirsMtimesUnicode(dirs, yieldcall = None):
	list = {}
	for directory in dirs:
		directory = os.path.expanduser(directory.replace("//","/"))

		u_directory = u"%s" %directory
		str_directory = str(directory)
		if hiddenCheck(u_directory):
			continue

		try:
			if win32:
				contents = dircache.listdir(u_directory)
				mtime = os.path.getmtime(u_directory)
			else:
				contents = os.listdir(u_directory)
				mtime = os.path.getmtime(str_directory)
		except OSError, errtuple:
			message = _("Scanning Directory Error: %s Path: %s") % (errtuple, u_directory)
			print str(message)
			if log:
				log(message)
			displayTraceback(sys.exc_info()[2])
			continue
		list[str_directory] = mtime

		for filename in contents:
			path = os.path.join(directory, filename)
	
			# force Unicode for reading from disk in win32
			u_path = u"%s" % path
			s_path = str(path)

			try:
				isdir = os.path.isdir(u_path)
			except OSError, errtuple:
				message = _("Scanning Error: %s Path: %s") % (errtuple, u_path)
				print str(message)
				if log:
					log(message)
				continue
			try:
				mtime = os.path.getmtime(u_path)
			except OSError, errtuple:
				try:
					mtime = os.path.getmtime(s_path)
				except OSError, errtuple:
					message = _("Scanning Error: %s Path: %s") % (errtuple, u_path)
					print str(message)
					if log:
						log(message)
					continue
			else:
				if isdir:
					list[s_path] = mtime
					dircontents = getDirsMtimesUnicode([path])
					for k in dircontents:
						list[k] = dircontents[k]
				if yieldcall is not None:
					yieldcall()
	return list

# Get Modification Times
def getDirsMtimes(dirs, yieldcall = None):
	list = {}
	for directory in dirs:
		directory = os.path.expanduser(directory.replace("//","/"))

		if hiddenCheck(directory):
			continue

		try:
			contents = dircache.listdir(directory)
			mtime = os.path.getmtime(directory)
		except OSError, errtuple:
			message = _("Scanning Directory Error: %s Path: %s") % (errtuple, directory)
			print str(message)
			if log:
				log(message)
			displayTraceback(sys.exc_info()[2])
			continue

		list[directory] = mtime

		for filename in contents:
			path = os.path.join(directory, filename)


			try:
				isdir = os.path.isdir(path)
			except OSError, errtuple:
				message = _("Scanning Error: %s Path: %s") % (errtuple, path)
				print str(message)
				if log:
					log(message)
				continue
			try:
				mtime = os.path.getmtime(path)
			except OSError, errtuple:
				islink = False
				try:
					islink = os.path.islink(path)
				except OSError, errtuple2:
					print errtuple2
				if islink:
					message = _("Scanning Error: Broken link to directory: \"%s\" from Path: \"%s\". Repair or remove this link.") % (os.readlink(path), path)
				else:
					message = _("Scanning Error: %s Path: %s") % (errtuple, path)
				print str(message)
				if log:
					log(message)
				continue
			else:
				if isdir:
					list[path] = mtime
					dircontents = getDirsMtimes([path])
					for k in dircontents:
						list[k] = dircontents[k]
				if yieldcall is not None:
					yieldcall()
	return list
				
# Check for new files
def getFilesList(mtimes, oldmtimes, oldlist, yieldcall = None, progress=None, rebuild=False):
	""" Get a list of files with their filelength and 
	(if mp3) bitrate and track length in seconds """
	list = {}
	if len(mtimes):
		percent = 1.0 / len(mtimes)
	
	for directory in mtimes:
		directory = os.path.expanduser(directory)
		if progress:
			#print progress.get_fraction()+percent
			if progress.get_fraction()+percent <= 1.0:
				gobject.idle_add(progress.set_fraction,progress.get_fraction()+percent)

		if hiddenCheck(directory):
			continue
		if not rebuild and directory in oldmtimes:
			if mtimes[directory] == oldmtimes[directory]:
				if os.path.exists(directory):
					
					list[directory] = oldlist[directory]
					continue
				else:
					print "Dropping removed directory %s" % directory
					continue

		list[directory] = []

		try:
			contents = os.listdir(directory)
		except OSError, errtuple:
			print str(errtuple)
			if log:
				log(str(errtuple))
			continue

		for filename in contents:

			if hiddenCheck(filename):
				continue	
			path = os.path.join(directory, filename)
			try:

				isfile = os.path.isfile(path)
			except OSError, errtuple:
				message = _("Scanning Error: %s Path: %s") % (errtuple, path)
				print str(message)
				if log:
					log(message)
				displayTraceback(sys.exc_info()[2])
				continue
			else:
				if isfile:
					# It's a file, check if it is mp3 or ogg
					data = getFileInfo(filename, path)
					if data is not None:
						list[directory].append(data)
			if yieldcall is not None:
				yieldcall()

	return list

# Check for new files
def getFilesListUnicode(mtimes, oldmtimes, oldlist, yieldcall = None, progress=None, rebuild=False):
	""" Get a list of files with their filelength and 
	(if mp3) bitrate and track length in seconds """
	list = {}
	if len(mtimes):
		percent = 1.0 / len(mtimes)
	
	for directory in mtimes:
		directory = os.path.expanduser(directory)
		if progress:
			#print progress.get_fraction()+percent
			if progress.get_fraction()+percent <= 1.0:
				gobject.idle_add(progress.set_fraction,progress.get_fraction()+percent)
				
		# force Unicode for reading from disk
		u_directory = u"%s" %directory
		str_directory = str(directory)

		if hiddenCheck(directory):
			continue
		if not rebuild and directory in oldmtimes:
			if mtimes[directory] == oldmtimes[directory]:
				list[directory] = oldlist[directory]
				continue

		list[directory] = []

		try:
			contents = os.listdir(u_directory)
		except OSError, errtuple:
			print str(errtuple)
			if log:
				log(str(errtuple))
			continue

		for filename in contents:
			if hiddenCheck(filename):
				continue	
			path = os.path.join(directory, filename)
			s_path = str(path)
			ppath = unicode( path)

			s_filename = str(filename)
			try:
				# try to force Unicode for reading from disk
				isfile = os.path.isfile(ppath)
			except OSError, errtuple:
				message = _("Scanning Error: %s Path: %s") % (errtuple, ppath)
				print str(message)
				if log:
					log(message)
				displayTraceback(sys.exc_info()[2])
				continue
			else:
				if isfile:
					# It's a file, check if it is mp3
					data = getFileInfoUnicode(s_filename, s_path)
					if data is not None:
						list[directory].append(data)
			if yieldcall is not None:
				yieldcall()
	return list
			
# Get metadata for mp3s and oggs
def getFileInfoUnicode(name, pathname):
	try:
		if type(name) is str:
			name_f = u"%s" % name
			pathname_f =  u"%s" % pathname
		else:
			name_f = name
			pathname_f =  pathname
		try:
			size = os.path.getsize(pathname_f)
		except:
			size = os.path.getsize(pathname)
			
		if name[-4:].lower() == ".mp3":
			try:
				mp3info = mp3.detect_mp3(pathname_f)
			except:
				mp3info = mp3.detect_mp3(pathname)
			if mp3info:
				bitrateinfo = (mp3info["bitrate"], mp3info["vbr"])
				fileinfo = (name, size, bitrateinfo, mp3info["time"])
			else:
				fileinfo = (name, size, None, None)
		
		elif vorbis and (name[-4:].lower() == ".ogg"):

			try:
				try:
					vf = vorbis.VorbisFile(pathname_f)
				except:
					vf = vorbis.VorbisFile(pathname)
				time = int(vf.time_total(0))
				bitrate = vf.bitrate(0)/1000
				fileinfo = (name, size, (bitrate, 0), time)
			except:
				fileinfo = (name, size, None, None)
		else:
			fileinfo = (name, size, None, None)
		return fileinfo
	except Exception, errtuple:
		message = _("Scanning File Error: %s Path: %s") % (errtuple, pathname)
		if log:
			log(message)
		displayTraceback(sys.exc_info()[2])

# Get metadata for mp3s and oggs
def getFileInfo(name, pathname):
	try:
		size = os.path.getsize(pathname)
			
		if name[-4:].lower() == ".mp3":
			mp3info = mp3.detect_mp3(pathname)
			if mp3info:
				bitrateinfo = (mp3info["bitrate"], mp3info["vbr"])
				fileinfo = (name, size, bitrateinfo, mp3info["time"])
			else:
				fileinfo = (name, size, None, None)
		elif vorbis and (name[-4:].lower() == ".ogg"):
			try:
				vf = vorbis.VorbisFile(pathname)
				time = int(vf.time_total(0))
				bitrate = vf.bitrate(0)/1000
				fileinfo = (name, size, (bitrate, 0), time)
			except:
				fileinfo = (name, size, None, None)
		else:
			fileinfo = (name, size, None, None)
		return fileinfo
	except Exception, errtuple:
		message = _("Scanning File Error: %s Path: %s") % (errtuple, pathname)
		if log:
			log(message)
		displayTraceback(sys.exc_info()[2])
		
def getFilesStreams(mtimes, oldmtimes, oldstreams, newsharedfiles, yieldcall = None):
	streams = {}
	for directory in mtimes.keys():
		if hiddenCheck(directory):
			continue

		if directory in oldmtimes:
			if mtimes[directory] == oldmtimes[directory]:
				if os.path.exists(directory):
					# No change
					streams[directory] = oldstreams[directory]
					continue
				else:
					print "Dropping missing directory %s" % directory
					continue
				
		streams[directory] = getDirStream(newsharedfiles[directory])
		if yieldcall is not None:
			yieldcall()
	return streams

# Stop any dot directories
def hiddenCheck(direct):
	dirs = direct.split(os.sep)
	hidden = 0
	for dir in dirs:
		if dir.startswith("."):
			hidden = 1
			break
	return hidden

# Pack all files and metadata in directory
def getDirStream(dir):
	from slskmessages import SlskMessage
	msg = SlskMessage()
	stream = msg.packObject(len(dir))
	
	for file_and_meta in dir:
		stream += getByteStream(file_and_meta)
	return stream

# Pack a file's metadata
def getByteStream(fileinfo):
	from slskmessages import SlskMessage
	self = SlskMessage()
	
	size = fileinfo[1]
	size1 = size & 0xffffffff
	size2 = size >> 32
	
	stream = chr(1) + self.packObject(fileinfo[0]) + self.packObject(size1) + self.packObject(size2)
	if fileinfo[2] is not None:
		stream = stream + self.packObject('mp3') + self.packObject(3)
		stream = stream + self.packObject(0)+ self.packObject(fileinfo[2][0])+self.packObject(1)+ self.packObject(fileinfo[3])+self.packObject(2)+self.packObject(fileinfo[2][1])
	else:
		stream = stream + self.packObject('') + self.packObject(0)
	return stream

# Update Search index with new files
def getFilesIndex(mtimes, oldmtimes, shareddirs, newsharedfiles, yieldcall = None):
	wordindex = {}
	fileindex = {}
	index = 0
	
	for directory in mtimes.keys():
		
		if hiddenCheck(directory):
			continue
		for j in newsharedfiles[directory]:
			indexes = getIndexWords(directory, j[0], shareddirs)
			for k in indexes:
				wordindex.setdefault(k, []).append(index)
			fileindex[str(index)] = (os.path.join(directory, j[0]), )+j[1:]
			index += 1
		if yieldcall is not None:
			yieldcall()
	return wordindex, fileindex
		
# Collect words from filenames for Search index
def getIndexWords(dir, file, shareddirs):
	for i in shareddirs:
		if os.path.commonprefix([dir,i]) == i:
			dir = dir[len(i):]
	words = string.split(string.lower(string.translate(dir+' '+file, string.maketrans( string.punctuation, string.join([' ' for i in string.punctuation], '')))))
	# remove duplicates
	d = {}
	for x in words:
		d[x] = x
	return d.values()
     
def escapeCommand(filename):
	"""Escapes special characters for command execution"""
	escaped = ""
	for ch in filename:
		if ch not in string.ascii_letters+string.digits+"/":
			escaped += "\\"
		escaped += ch
	return escaped

def displayTraceback(exception=None):
	global log
	import traceback
	if exception is None:
		tb = traceback.format_tb(sys.exc_info()[2])
	else:
		tb = traceback.format_tb(exception)
	if log: log("Traceback: "+ str(sys.exc_info()[0].__name__) + ": "+str(sys.exc_info()[1]))
	for line in tb:
		if type(line) is tuple:
			xline = ""
			for item in line:
				xline += str(item) + " "
			line = xline

		line = line.strip("\n")
		if log:
			log(line)

	traceback.print_exc()

## Dictionary that's sorted alphabetically
# @param UserDict dictionary to be alphabetized	
class SortedDict(UserDict):
	## Constructor
	# @param self SortedDict
	def __init__(self):
		self.__keys__ = []
		self.__sorted__ = True
		UserDict.__init__(self)
		
	## Set key
	# @param self SortedDict
	# @param key dict key
	# @param value dict value
	def __setitem__(self, key, value):
		if not self.__dict__.has_key(key):
			self.__keys__.append(key) 
			self.__sorted__ = False   
		UserDict.__setitem__(self, key, value)
	## Delete key
	# @param self SortedDict
	# @param key dict key
	def __delitem__(self, key):
		self.__keys__.remove(key)
		UserDict.__delitem__(self, key)
	## Get keys
	# @param self SortedDict
	# @return __keys__ 
	def keys(self):
		if not self.__sorted__:
			self.__keys__.sort()
			self.__sorted__ = True
		return self.__keys__
	## Get items
	# @param self SortedDict
	# @return list of keys and items
	def items(self):
		if not self.__sorted__:
			self.__keys__.sort()
			self.__sorted__ = True
		for key in self.__keys__:
			yield key, self[key]
