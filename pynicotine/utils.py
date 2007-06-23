# Copyright (c) 2006-2007 daelstorm. All rights reserved.
#
# Based on code from Nicotine, original copyright note:
# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
# Based on code from PySoulSeek, original copyright note:
# Copyright (c) 2001-2003 Alexander Kanavin. All rights reserved

"""
This module contains utility fuctions.
"""

version = "1.2.9svn"
latesturl = "http://nicotine-plus.sourceforge.net/LATEST"

import string
import os.path
import os,dircache
import sys
import gobject
win32 = sys.platform.startswith("win")
frame = 0
log = 0
language = ""
try:
	import _mp3 as mp3
	print "Using C mp3 scanner"
except ImportError:
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
	return message
ChangeTranslation(language)
# Translation Function
def _(s):
	global tr_cache
	global langTranslation
	# Don't translate empty strings
	# Poedit uses empty strings as metadata
	if s == "": return s
	if not tr_cache.has_key(s):
		tr_cache[s] = langTranslation.gettext(s)
	return tr_cache[s]

def getServerList(url):
	""" Parse server text file from http://www.slsk.org and 
	return a list of servers """
	import urllib,string
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
def rescandirs(shared, sharedmtimes, sharedfiles, sharedfilesstreams, yieldfunction, progress=None, name=""):
	# Check for modified or new files
	# returns dict in format:  { Directory : mtime, ... }
	
	gobject.idle_add(progress.set_text, _("Checking for changes"))
	gobject.idle_add(progress.show)
	gobject.idle_add(progress.set_fraction, 0)
	newmtimes = getDirsMtimes(shared, yieldfunction)
	gobject.idle_add(progress.set_text, _("Scanning %s") % name)
	# Get list of files
	# returns dict in format { Directory : { File : metadata, ... }, ... }
	newsharedfiles = getFilesList(newmtimes, sharedmtimes, sharedfiles,yieldfunction, progress)

	# Pack shares data
	# returns dict in format { Directory : hex string of files+metadata, ... }
	gobject.idle_add(progress.set_text, _("Building DataBase"))
	newsharedfilesstreams = getFilesStreams(newmtimes, sharedmtimes, sharedfilesstreams, newsharedfiles, yieldfunction)
	
	# Update Search Index
	# newwordindex is a dict in format {word: [num, num, ..], ... } with num matching
	# keys in newfileindex
	# newfileindex is a dict in format { num: (path, size, (bitrate, vbr), length), ... }
	gobject.idle_add(progress.set_text, _("Building Index"))
	newwordindex, newfileindex = getFilesIndex(newmtimes, sharedmtimes, shared, newsharedfiles, yieldfunction)
	gobject.idle_add(progress.set_fraction, 1.0)
	
	return newsharedfiles, newsharedfilesstreams, newwordindex, newfileindex, newmtimes
    

# Get Modification Times
def getDirsMtimes(dirs, yieldcall = None):
	list = {}
	for directory in dirs:
		directory = directory.replace("//","/")
		if win32:
			# force Unicode for reading from disk
			directory = u"%s" %directory
		if hiddenCheck(directory):
			continue
		try:
			contents = dircache.listdir(directory)
			mtime = os.path.getmtime(directory)
		except OSError, errtuple:
			message = _("Scanning Error: %s Path: %s") % (errtuple, directory)
			print message
			if log:
				log(message)
			continue
		if win32:
			# remove Unicode for saving in list
			directory = str(directory)
		list[directory] = mtime
		for filename in contents:
			if win32:
				# remove Unicode for saving in list
				filename = str(filename)
			path = os.path.join(directory, filename)
			if win32:
				# force Unicode for reading from disk
				path = u"%s" % path
			try:
				isdir = os.path.isdir(path)
				mtime = os.path.getmtime(path)
			except OSError, errtuple:
				message = _("Scanning Error: %s Path: %s") % (errtuple, path)
				print message
				if log:
					log(message)
				continue
			else:
				if win32:
					# remove Unicode for saving in list
					path = str(path)
				if isdir:
					list[path] = mtime
					dircontents = getDirsMtimes([path])
					for k in dircontents:
						list[k] = dircontents[k]
				if yieldcall is not None:
					yieldcall()
	return list
				
# Check for new files
def getFilesList(mtimes, oldmtimes, oldlist, yieldcall = None, progress=None):
	""" Get a list of files with their filelength and 
	(if mp3) bitrate and track length in seconds """
	list = {}
	if len(mtimes):
		percent = 1.0 / len(mtimes)
	
	for directory in mtimes:
		if progress:
			#print progress.get_fraction()+percent
			if progress.get_fraction()+percent <= 1.0:
				gobject.idle_add(progress.set_fraction,progress.get_fraction()+percent)
		if hiddenCheck(directory):

			continue	
		if oldmtimes.has_key(directory):
			if mtimes[directory] == oldmtimes[directory]:
				list[directory] = oldlist[directory]
				continue

		list[directory] = []
		if win32:
			# force Unicode for reading from disk
			directory = u"%s" %directory
		try:
			contents = dircache.listdir(directory)
		except OSError, errtuple:
			print errtuple
			if log:
				log(str(errtuple))
			continue
		if win32:
			# remove Unicode for saving in list
			directory = str(directory)
		for filename in contents:
			if win32:
				# remove Unicode for saving in list
				filename = str(filename)
			if hiddenCheck(filename):
				continue	
			path = os.path.join(directory, filename)
			if win32:
				# force Unicode for reading from disk
				path = u"%s" % path
			try:
				isfile = os.path.isfile(path)
			except OSError, errtuple:
				message = _("Scanning Error: %s Path: %s") % (errtuple, path)
				print message
				if log:
					log(message)
				continue
			else:
				if isfile:
					# It's a file, check if it is mp3
					list[directory].append(getFileInfo(filename, path))
			if yieldcall is not None:
				yieldcall()

	return list
			
# Get metadata for mp3s and oggs
def getFileInfo(name, pathname):
	size = os.path.getsize(pathname)
	if win32:
        	# remove Unicode for saving in list
        	name_f = str(name)
	else:
        	name_f = name
	if name[-4:].lower() == ".mp3":
		mp3info=mp3.detect_mp3(pathname)
		if mp3info:
			bitrateinfo = (mp3info["bitrate"],mp3info["vbr"])
			fileinfo = (name_f,size,bitrateinfo,mp3info["time"])
		else:
			fileinfo = (name_f,size,None,None)
	
	elif vorbis and (name[-4:].lower() == ".ogg"):

		try:
			vf = vorbis.VorbisFile(pathname)
			time = int(vf.time_total(0))
			bitrate = vf.bitrate(0)/1000
			fileinfo = (name_f,size, (bitrate,0), time)
		except:
			fileinfo = (name_f,size,None,None)
	else:
		fileinfo = (name_f,size,None,None)
	return fileinfo


def getFilesStreams(mtimes, oldmtimes, oldstreams, sharedfiles, yieldcall = None):
	streams = {}
	for i in mtimes.keys():
		if hiddenCheck(i):
			continue	
		if oldmtimes.has_key(i):
			if mtimes[i] == oldmtimes[i]:
				# No change
				streams[i] = oldstreams[i]
				continue
		streams[i] = getDirStream(sharedfiles[i])
		if yieldcall is not None:
			yieldcall()
	return streams

# Stop any dot directories
def hiddenCheck(direct):
	if win32:
		dirs = direct.split("\\")
	else:
		dirs = direct.split("/")
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
def getFilesIndex(mtimes, oldmtimes, shareddirs, sharedfiles, yieldcall = None):
	wordindex = {}
	fileindex = {}
	index = 0
	
	for i in mtimes.keys():
		
		if hiddenCheck(i):
			continue
		for j in sharedfiles[i]:
			indexes = getIndexWords(i,j[0],shareddirs)
			for k in indexes:
				wordindex.setdefault(k,[]).append(index)
			fileindex[str(index)] = (os.path.join(i,j[0]),)+j[1:]
			index += 1
		if yieldcall is not None:
			yieldcall()
	return wordindex, fileindex
		
# Collect words from filenames for Search index
def getIndexWords(dir, file, shareddirs):
	for i in shareddirs:
		if os.path.commonprefix([dir,i]) == i:
			dir = dir[len(i):]
	words = string.split(string.lower(string.translate(dir+' '+file, string.maketrans(string.punctuation,string.join([' ' for i in string.punctuation],'')))))
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
