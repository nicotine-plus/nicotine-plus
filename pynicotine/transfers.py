# Copyright (C) 2007 daelstorm. All rights reserved.
# -*- coding: utf-8 -*-
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
# Previous copyright below
# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
# Based on code from PySoulSeek, original copyright note:
# Copyright (c) 2001-2003 Alexander Kanavin. All rights reserved.

""" This module contains classes that deal with file transfers: the 
transfer manager.
"""

from __future__ import division

import slskmessages
import threading, thread
from slskmessages import newId
from logfacility import log

import os, stat, sys
import shutil
import os.path
import string, re
import time
import mp3
import locale
import utils
try:
	import hashlib
	MD5 = hashlib.md5
except:
	import md5
	MD5 = md5.new
from utils import _, executeCommand
from gtkgui.utils import recode2
from time import sleep
import gobject
win32 = sys.platform.startswith("win")

class Transfer(object):
	""" This class holds information about a single transfer. """
	def __init__(self, conn = None, user = None, filename = None, path = None, status = None, req=None, size = None, file = None, starttime = None, offset = None, currentbytes = None, speed = None, timeelapsed = None, timeleft = None, timequeued = None, transfertimer = None, requestconn = None, modifier = None, place = 0, bitrate = None, length = None):
		self.user = user
		self.filename = filename
		self.conn = conn
		self.path = path
		self.modifier = modifier
		self.req = req
		self.size = size
		self.file = file
		self.starttime = starttime
		self.lasttime = starttime
		self.offset = offset
		self.currentbytes = currentbytes
		self.lastbytes = currentbytes
		self.speed = speed
		self.timeelapsed = timeelapsed
		self.timeleft = timeleft
		self.timequeued = timequeued
		self.transfertimer = transfertimer
		self.requestconn = None
		self.place = place # Queue position
		self.bitrate = bitrate
		self.length = length
		self.setstatus(status)
	def setstatus(self, status):
		self.__status = status
		self.laststatuschange = time.time()
	def getstatus(self):
		return self.__status
	status = property(getstatus, setstatus)
class TransferTimeout:
	def __init__(self, req, callback):
		self.req = req
		self.callback = callback
	
	def timeout(self):
		self.callback([self])


class Transfers:
	""" This is the transfers manager"""
	def __init__(self, downloads, peerconns, queue, eventprocessor, users):
		self.peerconns = peerconns
		self.queue = queue
		self.eventprocessor = eventprocessor
		self.downloads = []
		self.uploads = []
		self.privilegedusers = []
		self.RequestedUploadQueue = []
		getstatus = {}
		for i in downloads:
			size = currentbytes = bitrate = length = None
			
			if len(i) >= 6:
				try: size = int(i[4])
				except: pass
				try: currentbytes = int(i[5])
				except: pass
			if len(i) >= 8:
				try: bitrate = i[6]
				except: pass
				try: length = i[7]
				except: pass
				
			if len(i) >= 4 and i[3] in ('Aborted', 'Paused'):
				status = 'Paused'
			else:
				status = 'Getting status'
			self.downloads.append(Transfer(user = i[0], filename=i[1], path=i[2], status=status, size=size, currentbytes=currentbytes, bitrate=bitrate, length=length))
			getstatus[i[0]] = ""
		for i in getstatus.keys():
			if i not in self.eventprocessor.watchedusers:
				self.queue.put(slskmessages.AddUser(i))
			self.queue.put(slskmessages.GetUserStatus(i))
		self.SaveDownloads()
		self.users = users
		self.downloadspanel = None
		self.uploadspanel = None
		
# queue sizes
		self.privcount = 0
		self.oggcount = 0
		self.usersqueued = {}
		self.privusersqueued = {}
		self.oggusersqueued = {}
		self.geoip = self.eventprocessor.geoip
		
	def setTransferPanels(self, downloads, uploads):
		self.downloadspanel = downloads
		self.uploadspanel = uploads

	def setPrivilegedUsers(self, list):
		for i in list:
			self.addToPrivileged(i)

	def addToPrivileged(self, user):
		if user not in self.privilegedusers:
			self.privilegedusers.append(user)
		if user in self.oggusersqueued:
			self.privusersqueued.setdefault(user, 0)
			self.privusersqueued[user] += self.oggusersqueued[user]
			self.privcount += self.oggusersqueued[user]
			self.oggcount -= self.oggusersqueued[user]
			del self.oggusersqueued[user]
		if user in self.usersqueued:
			self.privusersqueued.setdefault(user, 0)
			self.privusersqueued[user] += self.usersqueued[user]
			self.privcount += self.usersqueued[user]
			del self.usersqueued[user]

	def getAddUser(self, msg):
		""" Server tells us it'll notify us about a change in user's status """
		if not msg.userexists and self.eventprocessor.config.sections["ui"]["notexists"]:
			self.eventprocessor.logMessage(_("User %s does not exist") % (msg.user), 1)

	def GetUserStatus(self, msg):
		""" We get a status of a user and if he's online, we request a file from him """
		for i in self.downloads:
			if msg.user == i.user and i.status in ["Queued", 'Getting status', 'User logged off', 'Connection closed by peer', 'Aborted', 'Cannot connect', 'Paused']:
				if msg.status != 0:
					if i.status not in ["Queued", 'Aborted', 'Cannot connect', 'Paused' ]:
						self.getFile(i.user, i.filename, i.path, i)
				else:
					if i.status not in ['Aborted', 'Filtered']:
						i.status = "User logged off"
						self.downloadspanel.update(i)

		for i in self.uploads[:]:
			if msg.user == i.user and i.status != 'Finished':
				if msg.status != 0:
					if i.status == 'Getting status':
						self.pushFile(i.user, i.filename, i.path, i)
				else:
					if i.transfertimer is not None:
						i.transfertimer.cancel()
					self.uploads.remove(i)
					self.uploadspanel.update()
		if msg.status == 0:
			self.checkUploadQueue()


	def getFile(self, user, filename, path="", transfer = None, size=None, bitrate=None, length=None):
		path=utils.CleanPath(path, absolute=True)
		self.transferFile(0, user, filename, path, transfer, size, bitrate, length)

	def pushFile(self, user, filename, path="", transfer = None, size=None, bitrate=None, length=None ):
		if size is None:
			size = self.getFileSize(filename)
		self.transferFile(1, user, filename, path, transfer, size, bitrate, length)

	def transferFile(self, direction, user, filename, path="", transfer = None, size=None, bitrate=None, length=None):
		""" Get a single file. path is a local path. if transfer object is 
		not None, update it, otherwise create a new one."""
		if transfer is None:
			transfer = Transfer(user = user, filename= filename, path=path, status = 'Getting status', size=size, bitrate=bitrate, length=length)
			
			if direction == 0:
				self.downloads.append(transfer)
				self.SaveDownloads()
			else:
				self.uploads.append(transfer)
		else:
			transfer.status = 'Getting status'
		
		if user in self.users:
			status = self.users[user].status
		else:
			status = None

		if not direction and self.eventprocessor.config.sections["transfers"]["enablefilters"]:
			# Only filter downloads, never uploads!
			try:
				downloadregexp = re.compile(self.eventprocessor.config.sections["transfers"]["downloadregexp"], re.I)
				if downloadregexp.search(filename) is not None:
					self.eventprocessor.logMessage(_("Filtering: %s") % filename, 5)
					self.AbortTransfer(transfer)
					# The string to be displayed on the GUI
					transfer.status = 'Filtered'
					# In order to remove the filtered files from the saved download queue.
					self.SaveDownloads()
	
			except:
				pass
			
		if status is None:
			if user not in self.eventprocessor.watchedusers:
				self.queue.put(slskmessages.AddUser(user))
			self.queue.put(slskmessages.GetUserStatus(user))
		if transfer.status is not 'Filtered':
			transfer.req = newId()
			self.eventprocessor.ProcessRequestToPeer(user, slskmessages.TransferRequest(None, direction, transfer.req, filename, self.getFileSize(filename)))
		if direction == 0:
			self.downloadspanel.update(transfer)
		else:
			self.uploadspanel.update(transfer)


	def UploadFailed(self, msg):
		for i in self.peerconns:
			if i.conn is msg.conn.conn:
				user = i.username
				break
		else:
			return
		for i in self.downloads:
			if i.user == user and i.filename == msg.file and (i.conn is not None or i.status in ["Connection closed by peer", "Establishing connection", "Waiting for download"]):
				self.AbortTransfer(i)
				self.getFile(i.user, i.filename, i.path, i)
				self.eventprocessor.logTransfer(_("Retrying failed download: user %(user)s, file %(file)s") %{'user':i.user, 'file':self.decode(i.filename)}, 1)
				break
		else:
			self.eventprocessor.logTransfer(_("Failed download: user %(user)s, file %(file)s") %{'user':user, 'file':self.decode(msg.file)}, 1)

	def gettingAddress(self, req):
		for i in self.downloads:
			if i.req == req:
				i.status = "Getting address"
				self.downloadspanel.update(i)
		for i in self.uploads:
			if i.req == req:
				i.status = "Getting address"
				self.uploadspanel.update(i)

	def gotAddress(self, req):
		""" A connection is in progress, we got the address for a user we need
		to connect to."""
		for i in self.downloads:
			if i.req == req:
				i.status = "Connecting"
				self.downloadspanel.update(i)
		for i in self.uploads:
			if i.req == req:
				i.status = "Connecting"
				self.uploadspanel.update(i)


	def gotConnectError(self, req):
		""" We couldn't connect to the user, now we are waitng for him to 
		connect to us. Note that all this logic is handled by the network
		event processor, we just provide a visual feedback to the user."""
		for i in self.downloads:
			if i.req == req:
				i.status = "Waiting for peer to connect"
				self.downloadspanel.update(i)
		for i in self.uploads:
			if i.req == req:
				i.status = "Waiting for peer to connect"
				self.uploadspanel.update(i)

	def gotCantConnect(self, req):
		""" We can't connect to the user, either way. """
		for i in self.downloads:
			if i.req == req:
				i.status = "Cannot connect"
				i.req = None
				self.downloadspanel.update(i)
				if i.user not in self.eventprocessor.watchedusers:
					self.queue.put(slskmessages.AddUser(i.user))
				self.queue.put(slskmessages.GetUserStatus(i.user))
		for i in self.uploads:
			if i.req == req:
				i.status = "Cannot connect"
				i.req = None
				curtime = time.time()
				for j in self.uploads:
					if j.user == i.user:
						j.timequeued = curtime
				self.uploadspanel.update(i)
				if i.user not in self.eventprocessor.watchedusers:
					self.queue.put(slskmessages.AddUser(i.user))
				self.queue.put(slskmessages.GetUserStatus(i.user))
				self.checkUploadQueue()


	def gotFileConnect(self, req, conn):
		""" A transfer connection has been established, 
		now exchange initialisation messages."""
		for i in self.downloads:
			if i.req == req:
				i.status = "Initializing transfer"
				self.downloadspanel.update(i)
		for i in self.uploads:
			if i.req == req:
				i.status = "Initializing transfer"
				self.uploadspanel.update(i)

	def gotConnect(self, req, conn):
		""" A connection has been established, now exchange initialisation
		messages."""
		for i in self.downloads:
			if i.req == req:
				i.status = "Requesting file"
				i.requestconn = conn
				self.downloadspanel.update(i)
		for i in self.uploads:
			if i.req == req:
				i.status = "Requesting file"
				i.requestconn = conn
				self.uploadspanel.update(i)
	
	def TransferRequest(self, msg):
		user = response = None
		transfers = self.eventprocessor.config.sections["transfers"]
		if msg.conn is not None:
			for i in self.peerconns:
				if i.conn is msg.conn.conn:
					user = i.username
					conn = msg.conn.conn
					addr = msg.conn.addr[0]
		elif msg.tunneleduser is not None:
			user = msg.tunneleduser
			conn = None
			addr = "127.0.0.1"
		if user is None:
			self.eventprocessor.logMessage(_("Got transfer request %s but cannot determine requestor") % vars(msg), 5)
			return
	
		if msg.direction == 1:
			response = self.TransferRequestDownloads(msg, user, conn, addr)
			
		else:
			response = self.TransferRequestUploads(msg, user, conn, addr)
			
		if msg.conn is not None:
			self.queue.put(response)
		else:
			self.eventprocessor.ProcessRequestToPeer(user, response)
			
	def TransferRequestDownloads(self, msg, user, conn, addr):
		for i in self.downloads:
			if i.filename == msg.file and user == i.user and i.status == "Queued":
				# Remote peer is signalling a tranfer is ready, attempting to download it
				i.size = msg.filesize
				i.req = msg.req
				i.status = "Waiting for download"
				transfertimeout = TransferTimeout(i.req, self.eventprocessor.frame.callback)
				if i.transfertimer is not None:
					i.transfertimer.cancel()
				i.transfertimer = threading.Timer(30.0, transfertimeout.timeout)
				i.transfertimer.start()
				response = slskmessages.TransferResponse(conn, 1, req = i.req)
				self.downloadspanel.update(i)
				break
		else:
			# If this file is not in your download queue, then it must be
			# a remotely initated download and someone is manually uploading to you
			if self.CanUpload(user) and user in self.RequestedUploadQueue: 
				path = ""
				if self.eventprocessor.config.sections["transfers"]["uploadsinsubdirs"]:
					parentdir = msg.file.split("\\")[-2]
					path = self.eventprocessor.config.sections["transfers"]["uploaddir"]+os.sep+user+os.sep+parentdir

				transfer = Transfer(user = user, filename=msg.file , path=path, status = 'Getting status', size=msg.filesize, req=msg.req)
				self.downloads.append(transfer)
				self.SaveDownloads()
				if user not in self.eventprocessor.watchedusers:
					self.queue.put(slskmessages.AddUser(user))
				self.queue.put(slskmessages.GetUserStatus(user))
				if user != self.eventprocessor.config.sections["server"]["login"]:
					response = slskmessages.TransferResponse(conn, 0, reason = "Queued", req = transfer.req)
				self.downloadspanel.update(transfer)
				
			else:
				response = slskmessages.TransferResponse(conn, 0, reason = "Cancelled", req = msg.req)
				self.eventprocessor.logMessage(_("Denied file request: User %s, %s") % (user, str(vars(msg))), 5)
		return response
		
	def TransferRequestUploads(self, msg, user, conn, addr):
		"""
		Remote peer is requesting to download a file through
		your Upload queue
		"""
		
		# Check if the user is a buddy
		friend = user in [i[0] for i in self.eventprocessor.userlist.userlist]
		if friend and self.eventprocessor.config.sections["transfers"]["friendsnolimits"]:
			limits = 0
		else:
			limits = 1
		# Check user 'permissions'
		checkuser, reason = self.eventprocessor.CheckUser(user, addr)
		# checkuser is 1 if allowed
		# reason is a string
		realpath = self.eventprocessor.shares.virtual2real(msg.file)
		if not checkuser:
			response = slskmessages.TransferResponse(conn, 0, reason = reason, req=msg.req)
		elif not self.fileIsShared(user, msg.file, realpath):
			response = slskmessages.TransferResponse(conn, 0, reason = "File not shared", req = msg.req)
		elif self.fileIsQueued(user, msg.file):
			response = slskmessages.TransferResponse(conn, 0, reason = "Queued", req = msg.req)
		elif limits and self.queueLimitReached(user):
			uploadslimit = self.eventprocessor.config.sections["transfers"]["queuelimit"]
			response = slskmessages.TransferResponse(conn, 0, reason = "User limit of %i megabytes exceeded" %(uploadslimit), req = msg.req)
		elif limits and self.fileLimitReached(user):
			filelimit = self.eventprocessor.config.sections["transfers"]["filelimit"]
			limitmsg = "User limit of %i files exceeded" %(filelimit)
			response = slskmessages.TransferResponse(conn, 0, reason = limitmsg, req = msg.req)
		elif user in self.getTransferringUsers() or self.bandwidthLimitReached() or self.transferNegotiating():
			response = slskmessages.TransferResponse(conn, 0, reason = "Queued", req = msg.req)
			self.uploads.append(Transfer(user = user, filename = realpath, path = os.path.dirname(realpath), status = "Queued", timequeued = time.time(), size = self.getFileSize(msg.file), place = len(self.uploads)))
			self.uploadspanel.update(self.uploads[-1])
			self.addQueued(user, msg.file)
		else:
			size = self.getFileSize(realpath)
			response = slskmessages.TransferResponse(conn, 1, req = msg.req, filesize = size)
			transfertimeout = TransferTimeout(msg.req, self.eventprocessor.frame.callback) 
			self.uploads.append(Transfer(user = user, filename = realpath, path = os.path.dirname(realpath), status = "Waiting for upload", req = msg.req, size = size, place = len(self.uploads)))
			self.uploads[-1].transfertimer = threading.Timer(30.0, transfertimeout.timeout)
			self.uploads[-1].transfertimer.start()
			self.uploadspanel.update(self.uploads[-1])
			
		self.eventprocessor.logMessage(_("Upload request: %s") % str(vars(msg)), 5)
		return response

	def fileIsQueued(self, user, file):
		for i in self.uploads:
			if i.user == user and i.filename == file and i.status == "Queued":
				return 1
		return 0

	def queueLimitReached(self, user):
		uploadslimit = self.eventprocessor.config.sections["transfers"]["queuelimit"]*1024*1024
		if not uploadslimit:
			return False
		sizelist = [i.size for i in self.uploads if i.user == user and i.status == "Queued"]
		
		size = sum(sizelist)
		
		return size >= uploadslimit
	
	def fileLimitReached(self, user):
		filelimit = self.eventprocessor.config.sections["transfers"]["filelimit"]
		if not filelimit:
			return False
		numfiles = len([i for i in self.uploads if i.user == user and i.status == "Queued"])
		
		return numfiles >= filelimit
	
	def QueueUpload(self, msg):
		"""
		Peer remotely(?) queued a download (upload here)
		"""
		user = None
		for i in self.peerconns:
			if i.conn is msg.conn.conn:
				user = i.username
		if user is None:
			return
		addr = msg.conn.addr[0]
		realpath = self.eventprocessor.shares.virtual2real(msg.file)
		if not self.fileIsQueued(user, msg.file):
			friend = user in [i[0] for i in self.eventprocessor.userlist.userlist]
			if friend and self.eventprocessor.config.sections["transfers"]["friendsnolimits"]:
				limits = 0
			else:
				limits = 1
			
			checkuser, reason = self.eventprocessor.CheckUser(user, addr)
			if not checkuser:
				self.queue.put(slskmessages.QueueFailed(conn = msg.conn.conn, file = msg.file, reason = reason))
			elif limits and self.queueLimitReached(user):
				uploadslimit = self.eventprocessor.config.sections["transfers"]["queuelimit"]
				limitmsg = "User limit of %i megabytes exceeded" %(uploadslimit)
				self.queue.put(slskmessages.QueueFailed(conn = msg.conn.conn, file = msg.file, reason = limitmsg))
			elif limits and self.fileLimitReached(user):
				filelimit = self.eventprocessor.config.sections["transfers"]["filelimit"]
				limitmsg = "User limit of %i files exceeded" %(filelimit)
				self.queue.put(slskmessages.QueueFailed(conn = msg.conn.conn, file = msg.file, reason = limitmsg))
			elif self.fileIsShared(user, msg.file, realpath):
				self.uploads.append(Transfer(user = user, filename = realpath, path = os.path.dirname(realpath), status = "Queued", timequeued = time.time(), size = self.getFileSize(msg.file)))
				self.uploadspanel.update(self.uploads[-1])
				self.addQueued(user, msg.file)
			else:
				self.queue.put(slskmessages.QueueFailed(conn = msg.conn.conn, file = msg.file, reason = "File not shared" ))
		self.eventprocessor.logMessage(_("Queued upload request: User %s, %s") % (user, str(vars(msg))), 5)
		self.checkUploadQueue()

	def UploadQueueNotification(self, msg):
		username = None
		for i in self.peerconns:
			if i.conn is msg.conn.conn:
				username = i.username
				break
		if username is None:
			return
		if self.CanUpload(username):
			self.eventprocessor.logMessage(_("Your buddy, %s, is attempting to upload file(s) to you.")%(username), None)
			if username not in self.RequestedUploadQueue:
				self.RequestedUploadQueue.append(username)
		else:
			self.queue.put(slskmessages.MessageUser(username, _("[Automatic Message] ")+_("You are not allowed to send me files.")) )
			self.eventprocessor.logMessage(_("%s is not allowed to send you file(s), but is attempting to, anyway. Warning Sent.")%(username), None)
			return
			
	def CanUpload(self, user):
		transfers = self.eventprocessor.config.sections["transfers"]
		if transfers["remotedownloads"] == 1:
			# Remote Uploads only for users in list
			if transfers["uploadallowed"] == 2:
				# Users in userlist
				if user not in [i[0] for i in self.eventprocessor.userlist.userlist]:
					# Not a buddy
					return
			elif transfers["uploadallowed"] == 0:
				# No One can sent files to you
				return
			elif transfers["uploadallowed"] == 1:
				# Everyone can sent files to you
				pass
			elif transfers["uploadallowed"] == 3:
				# Trusted Users
				if user not in [i[0] for i in self.eventprocessor.userlist.userlist]:
					# Not a buddy
					return
				if user not in self.eventprocessor.userlist.trusted:
					# Not Trusted
					return
			return 1
		return 0
			
	def QueueFailed(self, msg):
		for i in self.peerconns:
			if i.conn is msg.conn.conn:
				user = i.username
		for i in self.downloads:
			if i.user == user and i.filename == msg.file and i.status == "Queued":
				i.status = msg.reason
				self.downloadspanel.update(i)
				break


	def fileIsShared(self, user, virtualfilename, realfilename):
		if win32:
			u_realfilename    = u"%s" % realfilename
			u_virtualfilename = u"%s" % virtualfilename
		else:
			u_realfilename    = realfilename
			u_virtualfilename = virtualfilename
		u_realfilename = u_realfilename.replace("\\", os.sep)
		u_virtualfilename = u_virtualfilename.replace("\\", os.sep)
		if not os.access(u_realfilename, os.R_OK):
			return False
		dir = os.path.dirname(u_virtualfilename)
		file = os.path.basename(u_virtualfilename)
		if self.eventprocessor.config.sections["transfers"]["enablebuddyshares"]:
			if user in [i[0] for i in self.eventprocessor.config.sections["server"]["userlist"]]:
				bshared = self.eventprocessor.config.sections["transfers"]["bsharedfiles"]
				for i in bshared.get(str(dir), ''):
					if file == i[0]:
						return True
		shared = self.eventprocessor.config.sections["transfers"]["sharedfiles"]
		for i in shared.get(str(dir), ''):
			if file == i[0]:
				return True
		return False

	def getTransferringUsers(self):
		return [i.user for i in self.uploads if i.req is not None or i.conn is not None or i.status == 'Getting status'] #some file is being transfered
	
	def transferNegotiating(self):
		# some file is being negotiated
		#return len([i for i in self.uploads if i.req is not None or (i.conn is not None and i.speed is None) or i.status == 'Getting status']) > 0 
		now = time.time()
		for i in self.uploads:
			if (now - i.laststatuschange) < 30: # if a status hasn't changed in the last 30 seconds the connection is probably never going to work, ignoring it.
				if i.req is not None:
					return True
				if i.conn is not None and i.speed is None:
					return True
				if i.status == 'Getting status':
					return True
		return False

	def bandwidthLimitReached(self):
		maxbandwidth = self.eventprocessor.config.sections["transfers"]["uploadbandwidth"]
		maxupslots = self.eventprocessor.config.sections["transfers"]["uploadslots"]
		useupslots = self.eventprocessor.config.sections["transfers"]["useupslots"]
		bandwidthlist = [i.speed for i in self.uploads if i.conn is not None and i.speed is not None]
		slotsreached = len(bandwidthlist) >= maxupslots
		if useupslots:
			return slotsreached
		else:
			return (sum(bandwidthlist) > maxbandwidth)

	
	def getFileSize(self, filename):
		try:
			if win32:
				size = os.path.getsize(u"%s" % filename.replace("\\", os.sep))
			else:
				size = os.path.getsize(filename.replace("\\", os.sep))
		except:
			# file doesn't exist (remote files are always this)
			size = 0
		return size

	def TransferResponse(self, msg):
		""" Got a response to the file request from the peer."""
		if msg.reason != None:
			for i in (self.downloads+self.uploads)[:]:
				if i.req != msg.req:
					continue
				i.status = msg.reason
				i.req = None
				self.downloadspanel.update(i)
				self.uploadspanel.update(i)
				if msg.reason == "Queued":
					if i.user not in self.users or self.users[i.user].status is None:
						if i.user not in self.eventprocessor.watchedusers:
							self.queue.put(slskmessages.AddUser(i.user))
						self.queue.put(slskmessages.GetUserStatus(i.user))
					if i in self.uploads:
						if i.transfertimer is not None:
							i.transfertimer.cancel()
						self.uploads.remove(i)
						self.uploadspanel.update()
					if i in self.downloads:
						self.eventprocessor.ProcessRequestToPeer(i.user, slskmessages.PlaceInQueueRequest(None, i.filename))
				self.checkUploadQueue()
				
		elif msg.filesize != None:
			for i in self.downloads:
				if i.req != msg.req:
					continue
				i.size = msg.filesize
				i.status = "Establishing connection"
				#Have to establish 'F' connection here
				self.eventprocessor.ProcessRequestToPeer(i.user, slskmessages.FileRequest(None, msg.req))
				self.downloadspanel.update(i)
				break
		else:
			for i in self.uploads:
				if i.req != msg.req:
					continue
				i.status = "Establishing connection"
				self.eventprocessor.ProcessRequestToPeer(i.user, slskmessages.FileRequest(None, msg.req))
				self.uploadspanel.update(i)
				self.checkUploadQueue()
				break
			else:
				self.eventprocessor.logMessage(_("Got unknown transfer response: %s") % str(vars(msg)), 5)

	def TransferTimeout(self, msg):
		for i in (self.downloads+self.uploads)[:]:
			if i.req != msg.req:
				continue
			if i.status in ["Queued", 'User logged off', 'Finished', 'Filtered', 'Aborted', 'Paused', 'Cancelled']:
				continue
			i.status = "Cannot connect"
			i.req = None
			curtime = time.time()
			for j in self.uploads:
				if j.user == i.user:
					j.timequeued = curtime
			if i.user not in self.eventprocessor.watchedusers:
				self.queue.put(slskmessages.AddUser(i.user))
			self.queue.put(slskmessages.GetUserStatus(i.user))
			self.downloadspanel.update(i)
			self.uploadspanel.update(i)
		self.checkUploadQueue()

	def FileRequest(self, msg):
		""" Got an incoming file request. Could be an upload request or a 
		request to get the file that was previously queued"""
	
		downloaddir = self.eventprocessor.config.sections["transfers"]["downloaddir"]
		incompletedir = self.eventprocessor.config.sections["transfers"]["incompletedir"]

		for i in self.downloads:
			if msg.req == i.req and i.conn is None and i.size is not None:
				i.conn = msg.conn
				i.req = None
				if i.transfertimer is not None:
					i.transfertimer.cancel()
				if not incompletedir:
					if i.path and i.path[0] == '/':
						incompletedir = utils.CleanPath(i.path)
					else:
						incompletedir = os.path.join(downloaddir, utils.CleanPath(i.path))
				incompletedir = self.encode(incompletedir, i.user)
				try:
					if not os.access(incompletedir, os.F_OK):
						os.makedirs(incompletedir)
					if not os.access(incompletedir, os.R_OK | os.W_OK | os.X_OK):
						raise OSError, "Download directory %s Permissions error.\nDir Permissions: %s" % (incompletedir, oct( os.stat(incompletedir)[stat.ST_MODE] & 0777))
						
				except OSError, strerror:
					self.eventprocessor.logMessage(_("OS error: %s") % strerror)
					i.status = "Download directory error"
					i.conn = None
					self.queue.put(slskmessages.ConnClose(msg.conn))
					self.eventprocessor.frame.NewNotification(_("OS error: %s") % strerror, title=_("Nicotine+ :: Directory download error"))
				
				else: 
					
					# also check for a windows-style incomplete transfer
					basename = string.split(i.filename,'\\')[-1]
					basename = self.encode(basename, i.user)
					winfname = os.path.join(incompletedir, "INCOMPLETE~"+basename)
					pyfname  = os.path.join(incompletedir, "INCOMPLETE"+basename)
					m = MD5()
					m.update(i.filename+i.user)
					
					pynewfname = os.path.join(incompletedir, "INCOMPLETE"+m.hexdigest()+basename)
					try:
						if os.access(winfname, os.F_OK):
							fname = winfname
						elif os.access(pyfname, os.F_OK):
							fname = pyfname
						else:
							fname = pynewfname
						
						if win32:
							f = open(u"%s" % fname, 'ab+')
						else:
							f = open(fname, 'ab+')
					except IOError, strerror:
						self.eventprocessor.logMessage(_("Download I/O error: %s") % strerror)
						i.status = "Local file error"
						try:
							f.close()
						except:
							pass
						i.conn = None
						self.queue.put(slskmessages.ConnClose(msg.conn))
					else:
						if self.eventprocessor.config.sections["transfers"]["lock"]:
							try:
								import fcntl
								try:
									fcntl.lockf(f, fcntl.LOCK_EX|fcntl.LOCK_NB)
								except IOError, strerror:
									self.eventprocessor.logMessage(_("Can't get an exclusive lock on file - I/O error: %s") % strerror)
							except ImportError:
								pass
						f.seek(0, 2)
						size = f.tell()
						self.queue.put(slskmessages.DownloadFile(i.conn, size, f, i.size))
						i.currentbytes = size
						#i.status = "%s" %(str(i.currentbytes))
						i.status = "Transferring"
						i.file = f
						i.place = 0
						i.offset = size
						i.starttime = time.time()
						self.eventprocessor.logMessage(_("Download started: %s") % (u"%s" % f.name), 5)

						self.eventprocessor.logTransfer(_("Download started: user %(user)s, file %(file)s") % {'user':i.user, 'file':u"%s" % f.name}, 5)
				self.SetIconDownloads()
				self.downloadspanel.update(i)
				
				return
			
		for i in self.uploads:
			if msg.req == i.req and i.conn is None:
				i.conn = msg.conn
				i.req = None
				if i.transfertimer is not None:
					i.transfertimer.cancel()
				try:
					# Open File
					if win32:
						filename = u"%s" % i.filename.replace("\\", os.sep)
					else:
						filename = i.filename.replace("\\", os.sep)
					f = open(filename,"rb")
					self.queue.put(slskmessages.UploadFile(i.conn, file = f, size = i.size))
					i.status = "Initializing transfer"
					i.file = f
					self.eventprocessor.logTransfer(_("Upload started: user %(user)s, file %(file)s") % {'user':i.user, 'file':self.decode(i.filename)})
				except IOError, strerror:
					self.eventprocessor.logMessage(_("Upload I/O error: %s") % strerror)
					i.status = "Local file error"
					try:
						f.close()
					except:
						pass
					i.conn = None
					self.queue.put(slskmessages.ConnClose(msg.conn))
				self.SetIconUploads()
				self.uploadspanel.update(i)
				break
		else:
			self.eventprocessor.logMessage(_("Unknown file request: %s") % str(vars(msg)), 1)
			self.queue.put(slskmessages.ConnClose(msg.conn))
            
	def SetIconDownloads(self):
		frame =  self.eventprocessor.frame
		if frame.MainNotebook.get_current_page() == frame.MainNotebook.page_num(frame.vboxdownloads):
			return
		tablabel = frame.GetTabLabel(frame.DownloadsTabLabel)
		if not tablabel:
			return
		tablabel.set_image(frame.images["online"])
		
	def SetIconUploads(self):
		frame =  self.eventprocessor.frame
		if frame.MainNotebook.get_current_page() == frame.MainNotebook.page_num(frame.vboxuploads):
			return
		tablabel = frame.GetTabLabel(frame.UploadsTabLabel)
		if not tablabel:
			return
		tablabel.set_image(frame.images["online"])
		
	def FileDownload(self, msg):
		""" A file download is in progress"""
		needupdate = 1
		config = self.eventprocessor.config.sections
		for i in self.downloads:
			if i.conn != msg.conn:
				continue
			try:
				if i.transfertimer is not None:
					i.transfertimer.cancel()
				curtime = time.time()
				i.currentbytes = msg.file.tell()
				if i.lastbytes is None:
					i.lastbytes = i.currentbytes
				if i.starttime is None:
					i.starttime = curtime
				if i.lasttime is None:
					i.lasttime = curtime - 1
				#i.status = "%s" %(str(i.currentbytes))
				i.status = "Transferring"
				oldelapsed = i.timeelapsed
				i.timeelapsed = curtime - i.starttime
				if curtime > i.starttime and i.currentbytes > i.offset:
					try:
						i.speed = (i.currentbytes - i.lastbytes)/(curtime - i.lasttime)/1024
					except ZeroDivisionError:
						i.speed = 0
					if i.speed <= 0.0:
						i.timeleft = "∞"
					else:
						i.timeleft = self.getTime((i.size - i.currentbytes)/i.speed/1024)
				i.lastbytes = i.currentbytes
				i.lasttime = curtime
				if i.size > i.currentbytes:
					if oldelapsed == i.timeelapsed:
						needupdate = 0
					#i.status = str(i.currentbytes)
					i.status = "Transferring"
				else:
					msg.file.close()
					basename = utils.CleanPath(self.encode(string.split(i.filename,'\\')[-1], i.user))
					downloaddir = config["transfers"]["downloaddir"]
					if i.path and i.path[0] == '/':
						folder = utils.CleanPath(i.path)
					else:
						folder = os.path.join(downloaddir, self.encode(i.path))
					if not os.access(folder, os.F_OK):
						os.makedirs(folder)
					(newname, identicalfile) = self.getRenamedEnhanced(os.path.join(folder, basename), msg.file.name)
					if newname:
						try:
							shutil.move(msg.file.name, newname)
						except (IOError, OSError), inst:
								try:
									shutil.move(msg.file.name, u"%s" % newname)
								except (IOError, OSError), inst:
									log.addwarning(_("Couldn't move '%(tempfile)s' to '%(file)s': %(error)s") % {'tempfile':self.decode(msg.file.name), 'file':self.decode(newname), 'error':str(inst)})
					i.status = "Finished"
					if newname:
						self.eventprocessor.logMessage(_("Download finished: %(file)s") % {'file':self.decode(newname)}, 5)
						self.eventprocessor.logTransfer(_("Download finished: user %(user)s, file %(file)s") % {'user':i.user, 'file':self.decode(i.filename)})
					else:
						self.eventprocessor.logMessage(_("File %(file)s is identical to %(identical)s, not saving.") % {'file':self.decode(msg.file.name), 'identical':identicalfile})
						self.eventprocessor.logTransfer(_("Download finished but not saved since it's a duplicate: user %(user)s, file %(file)s") % {'user':i.user, 'file':self.decode(i.filename)})
						
					self.queue.put(slskmessages.ConnClose(msg.conn))
					#if i.speed is not None:
						#self.queue.put(slskmessages.SendSpeed(i.user, int(i.speed*1024)))
						#Removed due to misuse. Replaced by SendUploadSpeed
					i.conn = None
					if newname:
						if win32:
							self.addToShared(u"%s" % newname)
						else:
							self.addToShared(newname)
						self.eventprocessor.shares.sendNumSharedFoldersFiles()
					self.SaveDownloads()
					self.downloadspanel.update(i)
					if config["transfers"]["shownotification"]:
						self.eventprocessor.frame.NewNotification(_("%(file)s downloaded from %(user)s") % {'user':i.user, "file":newname.rsplit(os.sep, 1)[1]}, title=_("Nicotine+ :: file downloaded"))

					if newname and config["transfers"]["afterfinish"]:
						if not executeCommand(config["transfers"]["afterfinish"], newname):
							self.eventprocessor.logMessage(_("Trouble executing '%s'") % config["transfers"]["afterfinish"])
						else:
							self.eventprocessor.logMessage(_("Executed: %s") % config["transfers"]["afterfinish"])
					if i.path and (config["transfers"]["shownotificationperfolder"] or config["transfers"]["afterfolder"]):
						# walk through downloads and break if any file in the same folder exists, else execute
						for ia in self.downloads:
							if ia.status not in ['Finished', 'Aborted', 'Paused', 'Filtered'] and ia.path and ia.path == i.path:
								break
						else:
							if config["transfers"]["shownotificationperfolder"]:
								self.eventprocessor.frame.NewNotification(_("%(folder)s downloaded from %(user)s") % {'user':i.user, "folder":folder}, title=_("Nicotine+ :: directory completed"))
							if config["transfers"]["afterfolder"]:
								if not executeCommand(config["transfers"]["afterfolder"], folder):
									self.eventprocessor.logMessage(_("Trouble executing on folder: %s") % config["transfers"]["afterfolder"])
								else:
									self.eventprocessor.logMessage(_("Executed on folder: %s") % config["transfers"]["afterfolder"])
			except IOError, strerror:
				self.eventprocessor.logMessage(_("Download I/O error: %s") % self.decode(strerror))
				i.status = "Local file error"
				try:
					msg.file.close()
				except:
					pass
				i.conn = None
				self.queue.put(slskmessages.ConnClose(msg.conn))
			if needupdate:
				self.downloadspanel.update(i)
    
	def addToShared(self, name):
		self.eventprocessor.shares.addToShared(name)
		""" Add a file to the normal shares database """
	
	def FileUpload(self, msg):
		""" A file upload is in progress"""
		needupdate = 1
	
		for i in self.uploads:
			if i.conn != msg.conn:
				continue
			if i.transfertimer is not None:
				i.transfertimer.cancel()
			curtime = time.time()
			if i.starttime is None:
				i.starttime = curtime
				i.offset = msg.offset
			lastspeed = 0
			if i.speed is not None:
				lastspeed = i.speed
			
			i.currentbytes = msg.offset + msg.sentbytes
			oldelapsed = i.timeelapsed
			i.timeelapsed = curtime - i.starttime
			if curtime > i.starttime and i.currentbytes > i.offset:
				try:
					i.speed = (i.currentbytes - i.lastbytes)/(curtime - i.lasttime)/1024
				except ZeroDivisionError:
					i.speed = lastspeed # too fast!
				if i.speed <= 0.0 and (i.currentbytes != i.size or lastspeed == 0):
					i.timeleft = "∞"
				else:
					if (i.currentbytes == i.size) and i.speed == 0:
						i.speed = lastspeed
					i.timeleft = self.getTime((i.size - i.currentbytes)/i.speed/1024)
				self.checkUploadQueue()
			i.lastbytes = i.currentbytes
			i.lasttime = curtime
			if i.size > i.currentbytes:
				if oldelapsed == i.timeelapsed:
					needupdate = 0
				#i.status = str(i.currentbytes)
				i.status = "Transferring"
			
				if i.user in self.privilegedusers:
					i.modifier = _("(privileged)")
				elif self.UserListPrivileged(i.user):
					i.modifier = _("(friend)")
			elif i.size is None:
				## Failed?
				self.checkUploadQueue()
				sleep(0.01)
			else:
				msg.file.close()
				i.status = "Finished"
				if i.speed is not None:
					self.queue.put(slskmessages.SendUploadSpeed(int(i.speed*1024)))
				#i.conn = None
				#self.queue.put(slskmessages.ConnClose(msg.conn))
				for j in self.uploads:
					if j.user == i.user:
						j.timequeued = curtime
				self.eventprocessor.logTransfer(_("Upload finished: %(user)s, file %(file)s") % {'user':i.user, 'file':self.decode(i.filename)})
				self.checkUploadQueue()
				self.uploadspanel.update(i)
				# Autoclear this upload
				if self.eventprocessor.config.sections["transfers"]["autoclear_uploads"]:
					self.uploads.remove(i)
					self.calcUploadQueueSizes()
					self.checkUploadQueue()
					self.uploadspanel.update()
			if needupdate:
				self.uploadspanel.update(i)

	def BanUser(self, user):
		"""
		Ban a user, cancel all the user's uploads, send a 'Banned'
		message via the transfers, and clear the transfers from the
		uploads list.
		"""
		if self.eventprocessor.config.sections["transfers"]["usecustomban"]:
			banmsg = _("Banned (%s)") % self.eventprocessor.config.sections["transfers"]["customban"]
		else:
			banmsg = _("Banned")
	
		list = [i for i in self.uploads if i.user == user]
		for upload in list:
			if upload.status == "Queued":
				self.eventprocessor.ProcessRequestToPeer(user, slskmessages.QueueFailed(None, file = upload.filename, reason = banmsg))
			else:
				self.AbortTransfer(upload)
		if self.uploadspanel is not None:
			self.uploadspanel.ClearByUser(user)
		if user not in self.eventprocessor.config.sections["server"]["banlist"]:
			self.eventprocessor.config.sections["server"]["banlist"].append(user)
			self.eventprocessor.config.writeConfig()
	
	# Find failed downloads and attempt to queue them
	def checkDownloadQueue(self):
		if self.eventprocessor.config.sections["transfers"]["autoretry_downloads"]:
			statuslist = ["Cannot connect", 'Connection closed by peer', "Local file error", "Getting address", "Waiting for peer to connect", "Initializing transfer"]
			for transfer in self.downloads:
				if transfer.status in statuslist:
					self.AbortTransfer(transfer)
					transfer.req = None
					self.getFile(transfer.user, transfer.filename, transfer.path, transfer)
			
			self.SaveDownloads()
					
	# Find next file to upload
	def checkUploadQueue(self):
		if self.bandwidthLimitReached() or self.transferNegotiating():
			return
		transfercandidate = None
		trusers = self.getTransferringUsers()
		
		# List of transfer instances of users who are not currently transferring
		list = [i for i in self.uploads if not i.user in trusers and i.status == "Queued"]
		# Sublist of privileged users transfers
		listprivileged = [i for i in list if self.isPrivileged(i.user)]

		if not self.eventprocessor.config.sections["transfers"]["fifoqueue"]:
			# Sublist of ogg files transfers
			listogg = [i for i in list if i.filename[-4:].lower() == ".ogg"]
			if len(listogg) > 0:
				# Only OGG files will get selected
				list = listogg
				
		if len(listprivileged) > 0:
			# Upload to a privileged user
			# Only Privileged users' files will get selected
			list = listprivileged
			
		if len(list) == 0:
			return

		if self.eventprocessor.config.sections["transfers"]["fifoqueue"]:
			# FIFO
			# Get the first item in the list
			transfercandidate = list[0]
		else:
			# Round Robin 
			# Get first transfer that was queued less than one second from now
			mintimequeued = time.time() + 1
			for i in list:
				if i.timequeued < mintimequeued:
					transfercandidate = i
					# Break loop
					mintimequeued = i.timequeued
					
		if transfercandidate is not None:
			self.pushFile(user = transfercandidate.user, filename = transfercandidate.filename, transfer = transfercandidate)
			self.removeQueued(transfercandidate.user, transfercandidate.filename)

	def PlaceInQueueRequest(self, msg):
		for i in self.peerconns:
			if i.conn is msg.conn.conn:
				user = i.username
		def listUsers():
			users = []
			for i in self.uploads:
				if i.user not in users:
					users.append(i.user)
			return users

		def countTransfers(username):
			transfers = []
			for i in self.uploads:
				if i.status == "Queued":
					if i.user == username:
						transfers.append(i)
			return len(transfers)

		if self.eventprocessor.config.sections["transfers"]["fifoqueue"]:
			# Number of transfers queued by non-privileged users
			count = 0
			# Number of transfers queued by privileged users
			countpriv = 0
			# Place in the queue for msg.file
			place = 0
			
			for i in self.uploads:
				# Ignore non-queued files
				if i.status == "Queued":
					if self.isPrivileged(i.user):
						countpriv += 1
					else:
						count += 1
					# Stop counting on the matching file
					if i.user == user and i.filename == msg.file:
						if self.isPrivileged(user):
							# User is privileged so we only 
							# count priv'd transfers
							place = countpriv
						else:
							# Count all transfers
							place = count + countpriv
						break
			# Debugging
			#print i.user, i.filename, count, countpriv, place
		else:
			# Todo
			list = listogg = listpriv = {user:time.time()}
			countogg = 0
			countpriv = 0
			trusers = self.getTransferringUsers()
			count = 0
			place = 0
			transfers = 0
			for i in self.uploads:
				# Ignore non-queued files
				if i.status == "Queued":
					if i.user == user:
						if self.isPrivileged(user):
							# User is privileged so we only 
							# count priv'd transfers
							listpriv[i.user] = i.timequeued
							place += 1
						else:
							# Count all transfers
							place += 1 
						# Stop counting on the matching file
						if i.filename == msg.file:
							break
			uploadUsers = listUsers()
			userTransfers = {}
			for username in uploadUsers:
				userTransfers[username] = countTransfers(username)
				if username is not user:
					if userTransfers[username] >= place:
						if username not in trusers:
							#print username, place
							transfers += place
					#else:
						#transfers += userTransfers[username]
			#print userTransfers, place, transfers
			place += transfers
			#print place
			#print trusers
	
		self.queue.put(slskmessages.PlaceInQueue(msg.conn.conn, msg.file, place))

	def getTime(self, seconds):
		sec = int(seconds % 60)
		minutes = int(seconds / 60 % 60)
		hours = int(seconds / 3600 % 24)
		days = int(seconds / 86400)
		
		time_string = "%02d:%02d:%02d" % (hours, minutes, sec)
		if days > 0:
			time_string = str(days) + "." + time_string
		return time_string

	def calcUploadQueueSizes(self):
	# queue sizes
		self.privcount = 0
		self.oggcount = 0
		self.usersqueued = {}
		self.privusersqueued = {}
		self.oggusersqueued = {}
	
		for i in self.uploads:
			if i.status == "Queued":
				self.addQueued(i.user, i.filename)

	def getUploadQueueSizes(self, username = None):
		if self.eventprocessor.config.sections["transfers"]["fifoqueue"]:
			count = 0
			for i in self.uploads:
				if i.status == "Queued":
					count += 1
			return count, count
		else:
			if self.isPrivileged(username):
				return len(self.privusersqueued), len(self.privusersqueued)
			else:
				return len(self.usersqueued)+self.privcount+self.oggcount, len(self.oggusersqueued)+self.privcount

	def addQueued(self, user, filename):
		if user in self.privilegedusers:
			self.privusersqueued.setdefault(user, 0)
			self.privusersqueued[user] += 1
			self.privcount += 1
		elif filename[-4:].lower() == ".ogg":
			self.oggusersqueued.setdefault(user, 0)
			self.oggusersqueued[user] += 1
			self.oggcount += 1
		else:
			self.usersqueued.setdefault(user, 0)
			self.usersqueued[user] += 1

	def removeQueued(self, user, filename):
		if user in self.privilegedusers:
			self.privusersqueued[user] -= 1
			self.privcount -= 1
			if self.privusersqueued[user] == 0:
				del self.privusersqueued[user]
		elif filename[-4:].lower() == ".ogg":
			self.oggusersqueued[user] -= 1
			self.oggcount -= 1
			if self.oggusersqueued[user] == 0:
				del self.oggusersqueued[user]
		else:
			self.usersqueued[user] -= 1
			if self.usersqueued[user] == 0:
				del self.usersqueued[user]

	def getTotalUploadsAllowed(self):
		list = [i for i in self.uploads if i.conn is not None]

		useupslots = self.eventprocessor.config.sections["transfers"]["useupslots"]

		if useupslots:
			maxupslots = self.eventprocessor.config.sections["transfers"]["uploadslots"]
			return maxupslots
		else:
			if self.bandwidthLimitReached():
				return len(list)
			else:
				return len(list)+1
	    
	
	def UserListPrivileged(self, user):
		# All users
		if self.eventprocessor.config.sections["transfers"]["preferfriends"]:
			return user in [i[0] for i in self.eventprocessor.config.sections["server"]["userlist"]]
		# Only privileged users
		userlist = [i[0] for i in self.eventprocessor.config.sections["server"]["userlist"]]
		if user not in userlist:
			return 0
		if self.eventprocessor.config.sections["server"]["userlist"][userlist.index(user)][3]:
			return 1
		else:
			return 0
		
	def isPrivileged(self, user):
		if user in self.privilegedusers or self.UserListPrivileged(user):
			return True
		else:
			return False 
		
	def ConnClose(self, conn, addr):
		""" The remote user has closed the connection either because
		he logged off, or because there's a network problem."""
		self.SaveDownloads()
		for i in self.downloads + self.uploads:
			if i.requestconn == conn and i.status == 'Requesting file':
				i.requestconn = None
				i.status = "Connection closed by peer"
				i.req = None
				self.downloadspanel.update(i)
				self.uploadspanel.update(i)
				self.checkUploadQueue()
			if i.conn != conn:
				continue
			if i.file is not None:
				i.file.close()
			if i.status != "Finished":
				if i.user in self.users and self.users[i.user].status == 0:
					i.status = "User logged off"
				else:
					#if i.status == 'Initializing transfer':
					#	illegal = set(utils.illegalwinchars).intersection(i.filename)
					#	if len(illegal) > 0:
					#		log.add(_("File transfer of %(file)s might have failed because of the %(chars)s characters in the name and because the other client is buggy.") % {'file':self.decode(i.filename), 'chars':''.join(illegal)})
					i.status = "Connection closed by peer"
					if i in self.downloads:
						self.eventprocessor.logTransfer(_("Retrying failed download: %(user)s, file %(file)s") % {'user':i.user, 'file':self.decode(i.filename)}, 1)
						
						self.getFile(i.user, i.filename, i.path, i)
			curtime = time.time()
			for j in self.uploads:
				if j.user == i.user:
					j.timequeued = curtime
			i.conn = None
			self.downloadspanel.update(i)
			self.uploadspanel.update(i)
			self.checkUploadQueue()

	def getRenamed(self, name):
		""" When a transfer is finished, we remove INCOMPLETE~ or INCOMPLETE 
		prefix from the file's name. """
		if win32 and not os.path.exists(u"%s" % name) and not os.path.exists(name):
			# Filename doesn't exist, good for renaming
			return name
		elif not win32 and not os.path.exists(name):
			return name
		else:
			# Append numbers to duplicate filenames so old files
			# do not get overwritten.
			n = 1
			while n < 1000:
				newname = name+"."+str(n)
				if not os.path.exists(newname):
					break
				n += 1
			return newname
	def getRenamedEnhanced(self, name, originalfile):
		""" When a transfer is finished, we remove INCOMPLETE~ or INCOMPLETE 
		prefix from the file's name. 
		
		Returns a tuple (newname, identicalfile) where precisely one of the two
		is None, and the other is a complete path. If newname is None a file
		with the same checksum value already exists as identicalfile, if
		identicalfile is None the file can be saved under newname."""
		if win32 and not os.path.exists(u"%s" % name) and not os.path.exists(name):
			# Filename doesn't exist, good for renaming
			return (name, None)
		elif not win32 and not os.path.exists(name):
			return (name, None)
		# A file with the same name already exists. First lets check whether it's a duplicate
		ourchecksum = self.getChecksum(originalfile)
		newname = name
		n = 1
		while n < 1000:
			existingchecksum = self.getChecksum(newname)
			if ourchecksum == existingchecksum:
				return (None, newname)
			newname = name+"."+str(n)
			if not os.path.exists(newname):
				break
			n += 1
		return (newname, None)
	def getChecksum(self, path):
		try:
			h = open(path)
			m = MD5()
			m.update(h.read(-1))
			digest = m.digest()
			h.close()
			return digest
		except IOError:
			return None

	def PlaceInQueue(self, msg):
		""" The server tells us our place in queue for a particular transfer."""
		
		username = None
		for i in self.peerconns:
			if i.conn is msg.conn.conn:
				username = i.username
				break
		
		if username:
			for i in self.downloads:
				if i.user != username:
					continue
				#print i.user
				if i.filename != msg.filename:
					continue
				#print i.filename.split('\\')[-1] 
				i.place = msg.place
				self.downloadspanel.update(i)
		
		#self.eventprocessor.logMessage(_("File: %(file)s, place in queue: %(place)s") % {'file':self.decode(msg.filename.split('\\')[-1]), 'place':msg.place})

	def FileError(self, msg):
		""" Networking thread encountered a local file error"""
		for i in self.downloads+self.uploads:
			if i.conn != msg.conn.conn:
				continue
			i.status = "Local file error"
			try:
				msg.file.close()
			except:
				pass
			i.conn = None
			self.queue.put(slskmessages.ConnClose(msg.conn.conn))
			self.eventprocessor.logMessage(_("I/O error: %s") % msg.strerror)
			self.downloadspanel.update(i)
			self.uploadspanel.update(i)
			self.checkUploadQueue()


	def FolderContentsResponse(self, msg):
		""" When we got a contents of a folder, get all the files in it, but
		skip the files in subfolders"""
		username = None
		for i in self.peerconns:
			if i.conn is msg.conn.conn:
				username = i.username
		if username is None:
			return
		for i in msg.list.keys():
			for directory in msg.list[i].keys():
				if os.path.commonprefix([i, directory]) == directory:
					priorityfiles = []
					normalfiles = []
					
					if self.eventprocessor.config.sections["transfers"]["prioritize"]:
						for file in msg.list[i][directory]:
							parts = file[1].rsplit('.', 1)
							if len(parts) == 2 and parts[1] in ['sfv','md5','nfo']:
								priorityfiles.append(file)
							else:
								normalfiles.append(file)
					else:
						normalfiles = msg.list[i][directory][:]
					if self.eventprocessor.config.sections["transfers"]["reverseorder"]:
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
							length = "%i:%02i" % (rl // 60, rl % 60)
						if directory[-1] == '\\':
							self.getFile(username, directory + file[1], self.FolderDestination(username, directory), size=file[2], bitrate=bitrate, length=length)
						else:
							self.getFile(username, directory + '\\' + file[1], self.FolderDestination(username, directory), size=file[2], bitrate=bitrate, length=length)
							
	def FolderDestination(self, user, directory):
		destination = ""
		if user in self.eventprocessor.requestedFolders:
			if directory in self.eventprocessor.requestedFolders[user]:
				destination += self.eventprocessor.requestedFolders[user][directory]
		if directory[-1] == '\\':
			parent = directory.split('\\')[-2]
			
		else:
			parent = directory.split('\\')[-1]
		destination = os.path.join(destination, parent)

		return destination
	def AbortTransfers(self):
		""" Stop all transfers """
		for i in self.downloads+self.uploads:
			if i.status in ( "Aborted", "Paused"):
				self.AbortTransfer(i)
				i.status = "Paused"
			elif i.status != "Finished":
				self.AbortTransfer(i)
				i.status = "Old"
				#self.downloadspanel.update()
				#self.uploadspanel.update()


	def AbortTransfer(self, transfer, remove = 0):
		if transfer.conn is not None:
			self.queue.put(slskmessages.ConnClose(transfer.conn))
			transfer.conn = None
		if transfer.transfertimer is not None:
			transfer.transfertimer.cancel()
		if transfer.file is not None:
			try:
				transfer.file.close()
				if remove:
					os.remove(transfer.file.name)
			except:
				pass
			if transfer in self.uploads:
				self.eventprocessor.logTransfer(_("Upload aborted, user %(user)s file %(file)s") % {'user':transfer.user, 'file':transfer.filename})
			else:
				self.eventprocessor.logTransfer(_("Download aborted, user %(user)s file %(file)s") % {'user':transfer.user, 'file':transfer.filename})

	def GetDownloads(self):
		""" Get a list of incomplete and not aborted downloads """
		return [ [i.user, i.filename, i.path, i.status, i.size, i.currentbytes, i.bitrate, i.length] for i in self.downloads if i.status != 'Finished']

	def SaveDownloads(self):
		""" Save list of files to be downloaded """
		self.eventprocessor.config.sections["transfers"]["downloads"] = self.GetDownloads()
		self.eventprocessor.config.writeTransfers()
	
	def decode(self, string):
		try:
			return string.decode(locale.nl_langinfo(locale.CODESET), "replace").encode("utf-8", "replace")
		except:
			return string
	
	def encode(self, string, user = None):
		coding = None
		config = self.eventprocessor.config.sections
		if user and user in config["server"]["userencoding"]:
			coding = config["server"]["userencoding"][user]
		string = self.eventprocessor.decode(string, coding)
		try:
			
			return string.encode(locale.nl_langinfo(locale.CODESET))
	#            return s.sencode(os.filesystemencoding(), "replace")
		except:
			return string
