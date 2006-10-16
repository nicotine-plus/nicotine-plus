# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
# Based on code from PySoulSeek, original copyright note:
# Copyright (c) 2001-2003 Alexander Kanavin. All rights reserved

"""
This module contains utility fuctions.
"""

version = "1.2.6pre1"
latesturl = "http://nicotine-plus.sourceforge.net/LATEST"

import string
import os.path
import os,dircache
import sys
win32 = sys.platform.startswith("win")
frame = 0
log = 0
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
def _(s):
	global tr_cache
	if not tr_cache.has_key(s):
		tr_cache[s] = gettext.gettext(s)
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

def rescandirs(shared, sharedmtimes, sharedfiles, sharedfilesstreams, yieldfunction):
        newmtimes = getDirsMtimes(shared,yieldfunction)
        newsharedfiles = getFilesList(newmtimes, sharedmtimes, sharedfiles,yieldfunction)
        newsharedfilesstreams = getFilesStreams(newmtimes, sharedmtimes, sharedfilesstreams, newsharedfiles,yieldfunction)
        newwordindex, newfileindex = getFilesIndex(newmtimes, sharedmtimes, shared, newsharedfiles,yieldfunction)
        return newsharedfiles,newsharedfilesstreams,newwordindex,newfileindex, newmtimes
    

def getDirsMtimes(dirs, yieldcall = None):
	list = {}
	for i in dirs:
		i = i.replace("//","/")
		if win32:
			# force Unicode for reading from disk
			i = u"%s" %i
		if hiddenCheck(i):
			continue
		try:
			contents = dircache.listdir(i)
			mtime = os.path.getmtime(i)
		except OSError, errtuple:
			print errtuple
			if log:
				log(str(errtuple))
			continue
		if win32:
			# remove Unicode for saving in list
			i = str(i)
		list[i] = mtime
		for f in contents:
			if win32:
				# remove Unicode for saving in list
				f = str(f)
			pathname = os.path.join(i, f)
			if win32:
				# force Unicode for reading from disk
				pathname = u"%s" % pathname
			try:
				isdir = os.path.isdir(pathname)
				mtime = os.path.getmtime(pathname)
			except OSError, errtuple:
				print errtuple
				if log:
					log(errtuple)
				continue
			else:
				if win32:
					# remove Unicode for saving in list
					pathname = str(pathname)
				if isdir:
					list[pathname] = mtime
					dircontents = getDirsMtimes([pathname])
					for k in dircontents:
						list[k] = dircontents[k]
				if yieldcall is not None:
					yieldcall()
	return list


def getFilesList(mtimes, oldmtimes, oldlist, yieldcall = None):
	""" Get a list of files with their filelength and 
	(if mp3) bitrate and track length in seconds """
	list = {}
	for i in mtimes:
		if hiddenCheck(i):
			continue	
		if oldmtimes.has_key(i):
			if mtimes[i] == oldmtimes[i]:
				list[i] = oldlist[i]
	    			continue

		list[i] = []
		if win32:
			# force Unicode for reading from disk
			i = u"%s" %i
		try:
			contents = dircache.listdir(i)
		except OSError, errtuple:
			print errtuple
			if log:
				log(str(errtuple))
			continue
		if win32:
			# remove Unicode for saving in list
			i = str(i)
		for f in contents:
			if win32:
				# remove Unicode for saving in list
				f = str(f)
			if hiddenCheck(f):
				continue	
			pathname = os.path.join(i, f)
			if win32:
				# force Unicode for reading from disk
				pathname = u"%s" %pathname
			try:
				isfile = os.path.isfile(pathname)
			except OSError, errtuple:
				print errtuple
				continue
			else:
				if isfile:
					# It's a file, check if it is mp3
					list[i].append(getFileInfo(f,pathname))
			if yieldcall is not None:
				yieldcall()
	
	return list

def getFileInfo(name, pathname):
    size = os.path.getsize(pathname)
    if win32:
        # remove Unicode for saving in list
        name_f = str(name)
    else:
        name_f = name
    if name[-4:] == ".mp3" or name[-4:] == ".MP3":
        mp3info=mp3.detect_mp3(pathname)
        if mp3info:
            bitrateinfo = (mp3info["bitrate"],mp3info["vbr"])
            fileinfo = (name_f,size,bitrateinfo,mp3info["time"])
        else:
            fileinfo = (name_f,size,None,None)
    elif vorbis and (name[-4:] == ".ogg" or name[-4:] == ".OGG"):

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
	    streams[i] = oldstreams[i]
	    continue
	streams[i] = getDirStream(sharedfiles[i])
        if yieldcall is not None:
            yieldcall()
    return streams
	
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
	
def getDirStream(dir):
    from slskmessages import SlskMessage
    msg = SlskMessage()
    stream = msg.packObject(len(dir))
    for i in dir:
	stream = stream + getByteStream(i)
    return stream
	
def getByteStream(fileinfo):
    from slskmessages import SlskMessage
    self = SlskMessage()
    stream = chr(1) + self.packObject(fileinfo[0]) + self.packObject(fileinfo[1]) + self.packObject(0)
    if fileinfo[2] is not None:
        stream = stream + self.packObject('mp3') + self.packObject(3)
        stream = stream + self.packObject(0)+ self.packObject(fileinfo[2][0])+self.packObject(1)+ self.packObject(fileinfo[3])+self.packObject(2)+self.packObject(fileinfo[2][1])
    else:
        stream = stream + self.packObject('') + self.packObject(0)
    return stream


def getFilesIndex(mtimes, oldmtimes, shareddirs,sharedfiles, yieldcall = None):
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

def getIndexWords(dir,file,shareddirs):
    import os.path,string
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
