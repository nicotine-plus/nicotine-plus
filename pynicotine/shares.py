# -*- coding: utf-8 -*-

# System imports
import dircache
import gobject
import string, sys, os
import time
import struct

# N+ imports
import slskmessages
from slskmessages import NetworkIntType, NetworkLongLongType
from logfacility import log
from utils import _, displayTraceback, strace
try:
	import metadata_mutagen as metadata
except ImportError:
	log.addwarning("Failed to import the Mutagen library, falling back to old library. To improve meta data please install Mutagen.")
	import mp3 as metadata

win32 = sys.platform.startswith("win")


class Shares:
	def __init__(self, np):
		self.np = np
		self.config = self.np.config
		self.queue = self.np.queue
		self.LogMessage = self.np.logMessage
		self.CompressedSharesBuddy = self.CompressedSharesNormal = None
		self.CompressShares("normal")
		self.CompressShares("buddy")
		self.requestedShares = {}
		self.newbuddyshares = self.newnormalshares = False
		self.translatepunctuation = string.maketrans(string.punctuation, string.join([' ' for i in string.punctuation],''))
	def real2virtual(self, path):
		for (virtual, real) in self._virtualmapping():
			if path == real:
				return virtual
			if path.startswith(real + os.sep):
				virtualpath = virtual + '\\' + path[len(real + os.sep):].replace(os.sep, '\\')
				return virtualpath
		return "???" + path
	def virtual2real(self, path):
		for (virtual, real) in self._virtualmapping():
			if path == virtual:
				return real
			if path.startswith(virtual + '\\'):
				realpath = real + path[len(virtual):].replace('\\', os.sep)
				return realpath
		return "__INTERNAL_ERROR__" + path
	def _virtualmapping(self):
		mapping = self.config.sections["transfers"]["shared"][:]
		if self.config.sections["transfers"]["enablebuddyshares"]:
			mapping += self.config.sections["transfers"]["buddyshared"]
		if self.config.sections["transfers"]["sharedownloaddir"]:
			mapping += [(_("Downloaded"), self.config.sections["transfers"]["downloaddir"])]
		return mapping
	def logMessage(self, message, debugLevel=0):
		if self.LogMessage is not None:
			gobject.idle_add(self.LogMessage, message, debugLevel)
	def sendNumSharedFoldersFiles(self):
		"""
		Send number of files in buddy shares if only buddies can
		download, and buddy-shares are enabled.
		"""
		conf = self.config.sections

		if conf["transfers"]["enablebuddyshares"] and conf["transfers"]["friendsonly"]:
			shared_db = "bsharedfiles"
		else:
			shared_db = "sharedfiles"
		sharedfolders = len(conf["transfers"][shared_db])
		sharedfiles = 0
		for i in conf["transfers"][shared_db].keys():
			sharedfiles += len(conf["transfers"][shared_db][i])
		self.queue.put(slskmessages.SharedFoldersFiles(sharedfolders, sharedfiles))

	def RescanShares(self, msg, rebuild=False):
		try:
			files, streams, wordindex, fileindex, mtimes = self.rescandirs(msg.shared, self.config.sections["transfers"]["sharedmtimes"], self.config.sections["transfers"]["sharedfiles"], self.config.sections["transfers"]["sharedfilesstreams"], msg.yieldfunction, self.np.frame.SharesProgress, name=_("Shares"), rebuild=rebuild)
			time.sleep(0.5)
			self.np.frame.RescanFinished([files, streams, wordindex, fileindex, mtimes], "normal")
		except Exception, ex:
			log.addwarning("Failed to rebuild share, serious error occurred. If this problem persists delete ~/.nicotine/*.db and try again. If that doesn't help please file a bug report with the stack trace included (see terminal output after this message). Technical details: %s" % ex)
			raise
		
	def RebuildShares(self, msg):
		self.RescanShares(msg, rebuild=True)
	
	def RebuildBuddyShares(self, msg):
		self.RescanBuddyShares(msg, rebuild=True)
	
	def RescanBuddyShares(self, msg, rebuild=False):
		files, streams, wordindex, fileindex, mtimes = self.rescandirs(msg.shared, self.config.sections["transfers"]["bsharedmtimes"], self.config.sections["transfers"]["bsharedfiles"], self.config.sections["transfers"]["bsharedfilesstreams"], msg.yieldfunction, self.np.frame.BuddySharesProgress, name=_("Buddy Shares"), rebuild=rebuild)
		time.sleep(0.5)
		self.np.frame.RescanFinished([files, streams, wordindex, fileindex, mtimes], "buddy")
		
	def CompressShares(self, sharestype):
		if sharestype == "normal":
			streams = self.config.sections["transfers"]["sharedfilesstreams"]
		elif sharestype == "buddy":
			streams = self.config.sections["transfers"]["bsharedfilesstreams"]

		if streams is None:
			message = _("ERROR: No %(type)s shares database available") % {"type": sharestype}
			print message
			self.logMessage(message, None)
			return
		
		m = slskmessages.SharedFileList(None, streams)
		m.makeNetworkMessage(nozlib=0, rebuild=True)
		
		if sharestype == "normal":
			self.CompressedSharesNormal = m
		elif sharestype == "buddy":
			self.CompressedSharesBuddy = m
        


	def GetSharedFileList(self, msg):
		self.logMessage("%s %s" %(msg.__class__, vars(msg)), 4)
		user = ip = port = None
		# Get peer's username, ip and port
		for i in self.np.peerconns:
			if i.conn is msg.conn.conn:
				
				user = i.username
				if i.addr is not None:
					if len(i.addr) != 2:
						break
					ip, port = i.addr
				break
		if user == None:
			# No peer connection
			return
		requestTime = time.time()
		if user in self.requestedShares:
			if not requestTime >  10 + self.requestedShares[user]:
				# Ignoring request, because it's 10 or less seconds since the
				# last one by this user
				return
		self.requestedShares[user] = requestTime
		# Check address is spoofed, if possible
		#if self.CheckSpoof(user, ip, port):
			# Message IS spoofed
		#	return
		if user == self.config.sections["server"]["login"]:
			if ip != None and port != None:
				self.logMessage(_("%(user)s is making a BrowseShares request, blocking possible spoofing attempt from IP %(ip)s port %(port)s") %{'user':user, 'ip':ip, 'port':port}, 1)
			else:
				self.logMessage(_("%(user)s is making a BrowseShares request, blocking possible spoofing attempt from an unknown IP & port") %{'user':user}, None)
			if msg.conn.conn != None:
				self.queue.put(slskmessages.ConnClose(msg.conn.conn))
			return
		self.logMessage(_("%(user)s is making a BrowseShares request") %{'user':user}, 1)
		addr = msg.conn.addr[0]
		checkuser, reason = self.np.CheckUser(user, addr)
	
		if checkuser == 1:
			## Send Normal Shares
			if self.newnormalshares:
				self.CompressShares("normal")
				self.newnormalshares = False
			m = self.CompressedSharesNormal

		elif checkuser == 2:
			## Send Buddy Shares
			if self.newbuddyshares:
				self.CompressShares("buddy")
				self.newbuddyshares = False
			m = self.CompressedSharesBuddy

		else:
			## Nyah, Nyah
			m = slskmessages.SharedFileList(msg.conn.conn, {})
			m.makeNetworkMessage(nozlib=0)


		m.conn = msg.conn.conn
		self.queue.put(m)
		

	def FolderContentsRequest(self, msg):
		username = None
		checkuser = None
		reason = ""
		for i in self.np.peerconns:
			if i.conn is msg.conn.conn:
				username = i.username
				checkuser, reason = self.np.CheckUser(username, None)
				break
		if not username:
			return
		if not checkuser:
			self.queue.put(slskmessages.MessageUser(username, "[Automatic Message] "+reason) )
			return
		elif self.config.sections["transfers"]["pmqueueddir"]:
			self.queue.put(slskmessages.MessageUser(username, "[Automatic Message] "+"Please try browsing me if you get 'File not shared' errors. You don't have to reply to this message." ) )
			
		if checkuser == 1:
			shares = self.config.sections["transfers"]["sharedfiles"]
		elif checkuser == 2:
			shares = self.config.sections["transfers"]["bsharedfiles"]
		else:
			response = self.queue.put(slskmessages.TransferResponse(msg.conn.conn, 0, reason = reason, req=0) )
			shares = {}
		
		if checkuser:
			if msg.dir.replace("\\", os.sep)[:-1] in shares:
				self.queue.put(slskmessages.FolderContentsResponse(msg.conn.conn, msg.dir, shares[msg.dir.replace("\\", os.sep)[:-1]]))
			elif msg.dir.replace("\\", os.sep) in shares:
				self.queue.put(slskmessages.FolderContentsResponse(msg.conn.conn, msg.dir, shares[msg.dir.replace("\\", os.sep)]))
			else:
				if checkuser == 2:
					shares = self.config.sections["transfers"]["sharedfiles"]
					if msg.dir.replace("\\", os.sep)[:-1] in shares:
						self.queue.put(slskmessages.FolderContentsResponse(msg.conn.conn, msg.dir, shares[msg.dir.replace("\\", os.sep)[:-1]]))
					elif msg.dir.replace("\\", os.sep) in shares:
						self.queue.put(slskmessages.FolderContentsResponse(msg.conn.conn, msg.dir, shares[msg.dir.replace("\\", os.sep)]))
					
				
		
		self.logMessage("%s %s" %(msg.__class__, vars(msg)), 4)

	def processExactSearchRequest(self, searchterm, user, searchid,  direct = 0, checksum=None):
		print searchterm, user, searchid, checksum
		pass
	
	def processSearchRequest(self, searchterm, user, searchid, direct = 0):
		if not self.config.sections["searches"]["search_results"]:
			# Don't return _any_ results when this option is disabled
			return
		if searchterm is None:
			return
		checkuser, reason = self.np.CheckUser(user, None)
		if not checkuser:
			return
		if reason == "geoip":
			geoip = 1
		else:
			geoip = 0
		maxresults = self.config.sections["searches"]["maxresults"]
		if checkuser == 2:
			wordindex = self.config.sections["transfers"]["bwordindex"]
			fileindex = self.config.sections["transfers"]["bfileindex"]
		else:
			wordindex = self.config.sections["transfers"]["wordindex"]
			fileindex = self.config.sections["transfers"]["fileindex"]
		fifoqueue = self.config.sections["transfers"]["fifoqueue"]
		if maxresults == 0:
			return
		terms = searchterm.translate(self.translatepunctuation).lower().split()
		list = [wordindex[i][:] for i in terms if i in wordindex]
		if len(list) != len(terms) or len(list) == 0:
			#self.logMessage(_("User %(user)s is searching for %(query)s, returning no results") %{'user':user, 'query':self.decode(searchterm)}, 2)
			return
		min = list[0]
		for i in list[1:]:
			if len(i) < len(min):
				min = i
		list.remove(min)
		for i in min[:]:
			for j in list:
				if i not in j:
					min.remove(i)
					break
		results = min[:maxresults]
		if len(results) > 0 and self.np.transfers is not None:
			queuesizes = self.np.transfers.getUploadQueueSizes()
			slotsavail = int(not self.np.transfers.bandwidthLimitReached())
			if len(results) > 0:
				message = slskmessages.FileSearchResult(None, self.config.sections["server"]["login"], geoip, searchid, results, fileindex, slotsavail, self.np.speed, queuesizes, fifoqueue)
				self.np.ProcessRequestToPeer(user, message)
				if direct:
					self.logMessage(_("User %(user)s is directly searching for %(query)s, returning %(num)i results") %{'user':user, 'query':self.np.decode(searchterm), 'num':len(results)}, 2)
				else:
					self.logMessage(_("User %(user)s is searching for %(query)s, returning %(num)i results") %{'user':user, 'query':self.np.decode(searchterm), 'num':len(results)}, 2)
					

	# Rescan directories in shared databases
	def rescandirs(self, shared, oldmtimes, oldfiles, sharedfilesstreams, yieldfunction, progress=None, name="", rebuild=False):
		"""
		Check for modified or new files via OS's last mtime on a directory,
		or, if rebuild is True, all directories
		"""
		#returns dict in format:  { Directory : mtime, ... }
		shared_directories = [x[1] for x in shared]

		gobject.idle_add(progress.set_text, _("Checking for changes"))
		gobject.idle_add(progress.show)
		gobject.idle_add(progress.set_fraction, 0)
		self.logMessage("Rescanning: Checking %(num)s directories" % {"num": len(oldmtimes)})
		if win32:
			newmtimes = self.getDirsMtimesUnicode(shared_directories, yieldfunction)
		else:
			newmtimes = self.getDirsMtimes(shared_directories, yieldfunction)
		self.logMessage("Rescanning: Found %(num)s directories" % {"num": len(newmtimes)})
		gobject.idle_add(progress.set_text, _("Scanning %s") % name)
		# Get list of files
		# returns dict in format { Directory : { File : metadata, ... }, ... }
		if win32:
			newsharedfiles = self.getFilesListUnicode(newmtimes, oldmtimes, oldfiles, yieldfunction, progress, rebuild)
		else:
			newsharedfiles = self.getFilesList(newmtimes, oldmtimes, oldfiles, yieldfunction, progress, rebuild)
		# Pack shares data
		# returns dict in format { Directory : hex string of files+metadata, ... }
		gobject.idle_add(progress.set_text, _("Building DataBase"))
		if win32:
			newsharedfilesstreams = self.getFilesStreamsUnicode(newmtimes, oldmtimes, sharedfilesstreams, newsharedfiles, yieldfunction)
		else:
			newsharedfilesstreams = self.getFilesStreams(newmtimes, oldmtimes, sharedfilesstreams, newsharedfiles, yieldfunction)
		
		# Update Search Index
		# newwordindex is a dict in format {word: [num, num, ..], ... } with num matching
		# keys in newfileindex
		# newfileindex is a dict in format { num: (path, size, (bitrate, vbr), length), ... }
		gobject.idle_add(progress.set_text, _("Building Index"))
		gobject.idle_add(progress.set_fraction, 0.0)
		newwordindex, newfileindex = self.getFilesIndex(newmtimes, oldmtimes, shared_directories, newsharedfiles, yieldfunction, progress)
		gobject.idle_add(progress.set_fraction, 1.0)
		return newsharedfiles, newsharedfilesstreams, newwordindex, newfileindex, newmtimes
	

	# Get Modification Times
	def getDirsMtimesUnicode(self, dirs, yieldcall = None):
		list = {}
		for directory in dirs:
			directory = os.path.expanduser(directory.replace("//","/"))

			u_directory = u"%s" %directory
			str_directory = str(directory)
			if self.hiddenCheck(u_directory):
				continue

			try:
				if win32:
					contents = dircache.listdir(u_directory)
					mtime = os.path.getmtime(u_directory)
				else:
					contents = os.listdir(u_directory)
					mtime = os.path.getmtime(str_directory)
			except OSError, errtuple:
				message = _("Scanning Directory Error: %(error)s Path: %(path)s") % {'error':errtuple, 'path':u_directory}
				print str(message)
				self.logMessage(message)
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
					message = _("Scanning Error: %(error)s Path: %(path)s") % {'error':errtuple, 'path':u_path}
					print str(message)
					self.logMessage(message)
					continue
				try:
					mtime = os.path.getmtime(u_path)
				except OSError, errtuple:
					try:
						mtime = os.path.getmtime(s_path)
					except OSError, errtuple:
						message = _("Scanning Error: %(error)s Path: %(path)s") % {'error':errtuple, 'path':u_path}
						print str(message)
						self.logMessage(message)
						continue
				else:
					if isdir:
						list[s_path] = mtime
						dircontents = self.getDirsMtimesUnicode([path])
						for k in dircontents:
							list[k] = dircontents[k]
					if yieldcall is not None:
						yieldcall()
		return list

	# Get Modification Times
	def getDirsMtimes(self, dirs, yieldcall = None):
		list = {}
		for directory in dirs:
			directory = os.path.expanduser(directory.replace("//","/"))

			if self.hiddenCheck(directory):
				continue

			try:
				contents = dircache.listdir(directory)
				mtime = os.path.getmtime(directory)
			except OSError, errtuple:
				message = _("Scanning Directory Error: %(error)s Path: %(path)s") % {'error':errtuple, 'path':directory}
				print str(message)
				self.logMessage(message)
				displayTraceback(sys.exc_info()[2])
				continue

			list[directory] = mtime
			for filename in contents:
				path = os.path.join(directory, filename)
				try:
					isdir = os.path.isdir(path)
				except OSError, errtuple:
					message = _("Scanning Error: %(error)s Path: %(path)s") % {'error':errtuple, 'path':path}
					print str(message)
					self.logMessage(message)
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
						message = _("Scanning Error: Broken link to directory: \"%(link)s\" from Path: \"%(path)s\". Repair or remove this link.") % {'link':os.readlink(path), 'path':path}
					else:
						message = _("Scanning Error: %(error)s Path: %(path)s") % {'error':errtuple, 'path':path}
					print str(message)
					self.logMessage(message)
					continue
				else:
					if isdir:
						list[path] = mtime
						dircontents = self.getDirsMtimes([path])
						for k in dircontents:
							list[k] = dircontents[k]
					if yieldcall is not None:
						yieldcall()
		return list
					
	# Check for new files
	def getFilesList(self, mtimes, oldmtimes, oldlist, yieldcall = None, progress=None, rebuild=False):
		""" Get a list of files with their filelength and 
		(if mp3) bitrate and track length in seconds """
		list = {}
		count = 0
		for directory in mtimes:
			directory = os.path.expanduser(directory)
			virtualdir = self.real2virtual(directory)
			count +=1
			if progress:
				percent = float(count)/len(mtimes)
				if percent <= 1.0:
					gobject.idle_add(progress.set_fraction, percent)

			if self.hiddenCheck(directory):
				continue
			if not rebuild and directory in oldmtimes:
				if mtimes[directory] == oldmtimes[directory]:
					if os.path.exists(directory):
						try:
							list[virtualdir] = oldlist[virtualdir]
							continue
						except KeyError:
							log.addwarning("Inconsistent cache for '%s', rebuilding '%s'" % (virtualdir, directory))
					else:
						print "Dropping removed directory %s" % directory
						continue

			list[virtualdir] = []

			try:
				contents = os.listdir(directory)
			except OSError, errtuple:
				print str(errtuple)
				self.logMessage(str(errtuple))
				continue

			for filename in contents:

				if self.hiddenCheck(filename):
					continue	
				path = os.path.join(directory, filename)
				try:

					isfile = os.path.isfile(path)
				except OSError, errtuple:
					message = _("Scanning Error: %(error)s Path: %(path)s") % {'error':errtuple, 'path':path}
					print str(message)
					self.logMessage(message)
					displayTraceback(sys.exc_info()[2])
					continue
				else:
					if isfile:
						# It's a file, check if it is mp3 or ogg
						data = self.getFileInfo(filename, path)
						if data is not None:
							list[virtualdir].append(data)
				if yieldcall is not None:
					yieldcall()

		return list

	# Check for new files
	def getFilesListUnicode(self, mtimes, oldmtimes, oldlist, yieldcall = None, progress=None, rebuild=False):
		""" Get a list of files with their filelength and 
		(if mp3) bitrate and track length in seconds """
		list = {}

		count = 0
		for directory in mtimes:
			directory = os.path.expanduser(directory)
			virtualdir = self.real2virtual(directory)
			count +=1
			if progress:
				percent = float(count)/len(mtimes)
				if percent <= 1.0:
					gobject.idle_add(progress.set_fraction, percent)
					
			# force Unicode for reading from disk
			u_directory = u"%s" %directory
			str_directory = str(directory)

			if self.hiddenCheck(directory):
				continue
			if not rebuild and directory in oldmtimes:
				if mtimes[directory] == oldmtimes[directory]:
					list[virtualdir] = oldlist[virtualdir]
					continue

			list[virtualdir] = []

			try:
				contents = os.listdir(u_directory)
			except OSError, errtuple:
				print str(errtuple)
				self.logMessage(str(errtuple))
				continue

			for filename in contents:
				if self.hiddenCheck(filename):
					continue	
				path = os.path.join(directory, filename)
				s_path = str(path)
				ppath = unicode( path)

				s_filename = str(filename)
				try:
					# try to force Unicode for reading from disk
					isfile = os.path.isfile(ppath)
				except OSError, errtuple:
					message = _("Scanning Error: %(error)s Path: %(path)s") % {'error':errtuple, 'path':path}
					print str(message)
					self.logMessage(message)
					displayTraceback(sys.exc_info()[2])
					continue
				else:
					if isfile:
						# It's a file, check if it is mp3
						data = self.getFileInfoUnicode(s_filename, s_path)
						if data is not None:
							list[virtualdir].append(data)
				if yieldcall is not None:
					yieldcall()
		return list
				
	# Get metadata for mp3s and oggs
	def getFileInfoUnicode(self, name, pathname):
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
				
			try:
				info = metadata.detect(pathname_f)
			except:
				info = metadata.detect(pathname)
			if info:
				bitrateinfo = (int(info["bitrate"]), int(info["vbr"]))
				fileinfo = (name, size, bitrateinfo, int(info["time"]))
			else:
				fileinfo = (name, size, None, None)
			return fileinfo
		except Exception, errtuple:
			message = _("Scanning File Error: %(error)s Path: %(path)s") % {'error':errtuple, 'path':pathname}
			self.logMessage(message)
			displayTraceback(sys.exc_info()[2])

	# Get metadata for mp3s and oggs
	def getFileInfo(self, name, pathname):
		try:
			size = os.path.getsize(pathname)
			info = metadata.detect(pathname)
			if info:
				bitrateinfo = (int(info["bitrate"]), int(info["vbr"]))
				fileinfo = (name, size, bitrateinfo, int(info["time"]))
			else:
				fileinfo = (name, size, None, None)
			return fileinfo
		except Exception, errtuple:
			message = _("Scanning File Error: %(error)s Path: %(path)s") % {'error':errtuple, 'path':pathname}
			self.logMessage(message)
			displayTraceback(sys.exc_info()[2])
			
	def getFilesStreamsUnicode(self, mtimes, oldmtimes, oldstreams, newsharedfiles, yieldcall = None):
		streams = {}
		shared = self.config.sections["transfers"]["shared"]
		virtual_dirs = [x[0] for x in shared]
		for directory in mtimes.keys():
			virtualdir = self.real2virtual(directory)
			# force Unicode for reading from disk
			u_directory = u"%s" % directory
			str_directory = str(directory)
			
			if self.hiddenCheck(directory):
				continue

			if directory in oldmtimes and directory not in oldstreams:
				# Partial information, happened with unicode paths that N+ couldn't handle properly
				del oldmtimes[directory]
			
			if directory in oldmtimes:
				if mtimes[directory] == oldmtimes[directory]:
					if os.path.exists(u_directory):
						# No change
						try:
							streams[virtualdir] = oldstreams[virtualdir]
							continue
						except KeyError:
							log.addwarning("Inconsistent cache for '%s', rebuilding '%s'" % (virtualdir, directory))
					else:
						print "2U. Dropping missing directory %s %s" % (type(u_directory), repr(u_directory))
						continue
			streams[virtualdir] = self.getDirStream(newsharedfiles[virtualdir])
			if yieldcall is not None:
				yieldcall()
		return streams
	def getFilesStreams(self, mtimes, oldmtimes, oldstreams, newsharedfiles, yieldcall = None):
		streams = {}
		shared = self.config.sections["transfers"]["shared"]
		for directory in mtimes.keys():
			virtualdir = self.real2virtual(directory)
			if self.hiddenCheck(directory):
				continue

			if directory in oldmtimes:
				if mtimes[directory] == oldmtimes[directory]:
					if os.path.exists(directory):
						# No change
						try:
							streams[virtualdir] = oldstreams[virtualdir]
							continue
						except KeyError:
							log.addwarning("Inconsistent cache for '%s', rebuilding '%s'" % (virtualdir, directory))
					else:
						print "2S. Dropping missing directory %s" % directory
						continue
					
			streams[virtualdir] = self.getDirStream(newsharedfiles[virtualdir])
			if yieldcall is not None:
				yieldcall()
		return streams
	
	# Stop any dot directories
	def hiddenCheck(self, direct):
		dirs = direct.split(os.sep)
		for dir in dirs:
			if dir.startswith("."):
				return True
		return False

	# Pack all files and metadata in directory
	def getDirStream(self, dir):
		msg = slskmessages.SlskMessage()
		#X print "stream-" + repr(msg.packObject(len(dir)))
		#X print "stream+" + repr(msg.packObject(NetworkIntType(len(dir))))
		stream = msg.packObject(NetworkIntType(len(dir)))
		
		for file_and_meta in dir:
			stream += self.getByteStream(file_and_meta)
		return stream

	# Pack a file's metadata
	def getByteStream(self, fileinfo):
		message = slskmessages.SlskMessage()
		
		stream = chr(1) + message.packObject(fileinfo[0]) + message.packObject(NetworkLongLongType(fileinfo[1]))
		if fileinfo[2] is not None:
			try:
				msgbytes = ''
				msgbytes += message.packObject('mp3') + message.packObject(3)
				msgbytes += (message.packObject(0) +
						message.packObject(NetworkIntType(fileinfo[2][0])) +
						message.packObject(1) +
						message.packObject(NetworkIntType(fileinfo[3])) +
						message.packObject(2) +
						message.packObject(NetworkIntType(fileinfo[2][1])))
				stream += msgbytes
			except struct.error:
				log.addwarning(_("Found meta data that couldn't be encoded, possible corrupt file: '%(file)s' has a bitrate of %(bitrate)s kbs, a length of %(length)s seconds and a VBR of %(vbr)s" % {
						'file':    fileinfo[0],
						'bitrate': fileinfo[2][0],
						'length':  fileinfo[3],
						'vbr':     fileinfo[2][1]
					}))
				stream += message.packObject('') + message.packObject(0)
		else:
			stream += message.packObject('') + message.packObject(0)
		return stream

	# Update Search index with new files
	def getFilesIndex(self, mtimes, oldmtimes, shareddirs, newsharedfiles, yieldcall = None, progress=None):
		wordindex = {}
		fileindex = {}
		index = 0
		count = 0
		for directory in mtimes.keys():
			virtualdir = self.real2virtual(directory)
			if progress:
				percent = float(count)/len(mtimes)
				if percent <= 1.0:
					gobject.idle_add(progress.set_fraction, percent)
			count +=1
			if self.hiddenCheck(directory):
				continue
			for j in newsharedfiles[virtualdir]:
				indexes = self.getIndexWords(virtualdir, j[0], shareddirs)
				for k in indexes:
					wordindex.setdefault(k, []).append(index)
				fileindex[str(index)] = ((virtualdir + '\\' + j[0]), )+j[1:]
				index += 1
			if yieldcall is not None:
				yieldcall()
		return wordindex, fileindex
			
	# Collect words from filenames for Search index
	def getIndexWords(self, dir, file, shareddirs):
		for i in shareddirs:
			if os.path.commonprefix([dir,i]) == i:
				dir = dir[len(i):]
		words = string.split(string.lower(string.translate(dir+' '+file, string.maketrans( string.punctuation, string.join([' ' for i in string.punctuation], '')))))
		# remove duplicates
		d = {}
		for x in words:
			d[x] = x
		return d.values()
		
	def addToShared(self, name):
		""" Add a file to the normal shares database """
		config = self.config.sections
		if not config["transfers"]["sharedownloaddir"]:
			return
		
		shared = config["transfers"]["sharedfiles"]
		sharedstreams = config["transfers"]["sharedfilesstreams"]
		wordindex = config["transfers"]["wordindex"]
		fileindex = config["transfers"]["fileindex"]
		shareddirs = config["transfers"]["shared"] + [config["transfers"]["downloaddir"]]
		sharedmtimes = config["transfers"]["sharedmtimes"]

		dir = str(os.path.expanduser(os.path.dirname(name)))
		str_name = str(name)
		file = str(os.path.basename(name))
		size = os.path.getsize(name)

		shared[dir] = shared.get(dir, [])

		if file not in [i[0] for i in shared[dir]]:
			fileinfo = self.getFileInfo(file, name)
			shared[dir] = shared[dir] + [fileinfo]
			sharedstreams[dir] = self.getDirStream(shared[dir])
			words = self.getIndexWords(dir, file, shareddirs)
			self.addToIndex(wordindex, fileindex, words, dir, fileinfo)
			sharedmtimes[dir] = os.path.getmtime(dir)
			self.newnormalshares = True
			
		if config["transfers"]["enablebuddyshares"]:
			self.addToBuddyShared(name)
			
		self.config.writeShares()
		
	def addToBuddyShared(self, name):
		""" Add a file to the buddy shares database """
		config = self.config.sections
		if not config["transfers"]["sharedownloaddir"]:
			return
		bshared = config["transfers"]["bsharedfiles"]
		bsharedstreams = config["transfers"]["bsharedfilesstreams"]
		bwordindex = config["transfers"]["bwordindex"]
		bfileindex = config["transfers"]["bfileindex"]
		bshareddirs = config["transfers"]["buddyshared"] + config["transfers"]["shared"] + [config["transfers"]["downloaddir"]]
		bsharedmtimes = config["transfers"]["bsharedmtimes"]
		
		dir = str(os.path.expanduser(os.path.dirname(name)))
		str_name = str(name)
		file = str(os.path.basename(name))
		size = os.path.getsize(name)
		
		bshared[dir] = bshared.get(dir, [])
		
		if file not in [i[0] for i in bshared[dir]]:
			fileinfo = self.getFileInfo(file, name)
			bshared[dir] = bshared[dir] + [fileinfo]
			bsharedstreams[dir] = self.getDirStream(bshared[dir])
			words = self.getIndexWords(dir, file, bshareddirs)
			self.addToIndex(bwordindex, bfileindex, words, dir, fileinfo)
			bsharedmtimes[dir] = os.path.getmtime(dir)
			
			self.newbuddyshares = True
			

	def addToIndex(self, wordindex, fileindex, words, dir, fileinfo):
		index = len(fileindex.keys())
		for i in words:
			if i not in wordindex:
				wordindex[i] = [index]
			else:
				wordindex[i] = wordindex[i] + [index]
		fileindex[str(index)] = (os.path.join(dir, fileinfo[0]),)+fileinfo[1:]


