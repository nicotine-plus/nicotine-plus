# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
# Based on code from PySoulSeek, original copyright note:
# Copyright (c) 2001-2003 Alexander Kanavin. All rights reserved.

""" This module contains classes that deal with file transfers: the 
transfer manager.
"""

import slskmessages
import threading
from slskmessages import newId

import os, stat
import os.path
import string
import time
import mp3
import locale
import utils
import md5
from utils import _
from gtkgui.utils import recode2

class Transfer:
    """ This class holds information about a single transfer. """
    def __init__(self, conn = None, user = None, filename = None, path = None, status = None, req=None, size = None, file = None, starttime = None, offset = None, currentbytes = None, speed = None,timeelapsed = None, timeleft = None, timequeued = None, transfertimer = None, requestconn = None, modifier = None):
	self.user = user
	self.filename = filename
	self.conn = conn
	self.path = path
	self.status = status
	self.modifier = modifier
	self.req = req
	self.size = size
	self.file = file
	self.starttime = starttime
	self.offset = offset
	self.currentbytes = currentbytes
	self.speed = speed
	self.timeelapsed = timeelapsed
	self.timeleft = timeleft
	self.timequeued = timequeued
	self.transfertimer = transfertimer
	self.requestconn = None

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
	getstatus = {}
	for i in downloads:
	    self.downloads.append(Transfer(user = i[0], filename=i[1], path=i[2], status = _('Getting status')))
	    getstatus[i[0]] = ""
	for i in getstatus.keys():
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
	
	try:
	    import GeoIP
	    self.geoip = GeoIP.new(GeoIP.GEOIP_STANDARD)
	except ImportError:
	    try:
	        import _GeoIP
	        self.geoip = _GeoIP.new(_GeoIP.GEOIP_STANDARD)
	    except:
	        self.geoip = None
 
    def setTransferPanels(self, downloads, uploads):
	self.downloadspanel = downloads
	self.uploadspanel = uploads

    def setPrivilegedUsers(self, list):
	for i in list:
	    self.addToPrivileged(i)    

    def addToPrivileged(self, user):
	self.privilegedusers.append(user)
	if self.oggusersqueued.has_key(user):
	    self.privusersqueued.setdefault(user,0)
	    self.privusersqueued[user] += self.oggusersqueued[user]
	    self.privcount += self.oggusersqueued[user]
	    self.oggcount -= self.oggusersqueued[user]
	    del self.oggusersqueued[user]
	if self.usersqueued.has_key(user):
	    self.privusersqueued.setdefault(user,0)
            self.privusersqueued[user] += self.usersqueued[user]
	    self.privcount += self.usersqueued[user]
	    del self.usersqueued[user]

    def getAddUser(self,msg):
	""" Server tells us it'll notify us about a change in user's status """
	if not msg.userexists:
	    self.eventprocessor.logMessage(_("User %s does not exist") % (msg.user))

    def GetUserStatus(self,msg):
	""" We get a status of a user and if he's online, we request a file from 	him """
	for i in self.downloads:
	    if msg.user == i.user and i.status in ['Queued', _('Getting status'), _('User logged off'), _('Connection closed by peer'), _('Aborted'), _('Cannot connect')]:
		if msg.status != 0:
		    if i.status not in ['Queued', _('Aborted'), _('Cannot connect')]:
                        self.getFile(i.user, i.filename, i.path, i)
	        else:
		    if i.status not in [_('Aborted')]:
                        i.status = _("User logged off")
		        self.downloadspanel.update(i)    

        for i in self.uploads[:]:
            if msg.user == i.user and i.status != _('Finished'):
                if msg.status != 0:
		    if i.status == _('Getting status'):
                        self.pushFile(i.user, i.filename, i.path, i)
                else:
		    if i.transfertimer is not None:
			i.transfertimer.cancel()
                    self.uploads.remove(i)
		    self.uploadspanel.update()
	if msg.status == 0:
	    self.checkUploadQueue()


    def getFile(self, user, filename, path="", transfer = None):
	self.transferFile(0,user,filename,path,transfer)

    def pushFile(self, user, filename, path="", transfer = None):
        self.transferFile(1,user,filename,path,transfer)

    def transferFile(self, direction, user, filename, path="", transfer = None):
	""" Get a single file. path is a local path. if transfer object is 
	not None, update it, otherwise create a new one."""
        if transfer is None:
	    transfer = Transfer(user = user, filename= filename, path=path, status = _('Getting status'))
            if direction == 0:
                self.downloads.append(transfer)
                self.SaveDownloads()
            else:
                self.uploads.append(transfer)
        else:
            transfer.status = _('Getting status')
        if self.users.has_key(user):
	    status = self.users[user].status
	else:
	    status = None
	if status is None:
	    self.queue.put(slskmessages.GetUserStatus(user))
	else:
	    transfer.req = newId()
	    self.eventprocessor.ProcessRequestToPeer(user,slskmessages.TransferRequest(None,direction,transfer.req,filename, self.getFileSize(filename)))
	if direction == 0:
   	    self.downloadspanel.update(transfer)
	else:
            self.uploadspanel.update(transfer)


    def UploadFailed(self,msg):
        for i in self.peerconns:
            if i.conn is msg.conn.conn:
                user = i.username
		break
	else:
	    return
	for i in self.downloads:
	    if i.user == user and i.filename == msg.file and (i.conn is not None or i.status in [_("Connection closed by peer"), _("Establishing connection")]):
		self.AbortTransfer(i)
		self.getFile(i.user, i.filename, i.path, i)
		self.eventprocessor.logTransfer(_("Retrying failed download: user %s, file %s") %(i.user,self.decode(i.filename)), 1)
		break
	else:
	    self.eventprocessor.logTransfer(_("Failed download: user %s, file %s") %(user,self.decode(msg.file)), 1)

    def gettingAddress(self, req):
	for i in self.downloads:
	    if i.req == req:
		i.status = _("Getting address")
                self.downloadspanel.update(i)
        for i in self.uploads:
            if i.req == req:
                i.status = _("Getting address")
                self.uploadspanel.update(i)

    def gotAddress(self, req):
	""" A connection is in progress, we got the address for a user we need
	to connect to."""
	for i in self.downloads:
	    if i.req == req:
		i.status = _("Connecting")
                self.downloadspanel.update(i)
        for i in self.uploads:
            if i.req == req:
                i.status = _("Connecting")
                self.uploadspanel.update(i)


    def gotConnectError(self,req):
	""" We couldn't connect to the user, now we are waitng for him to 
	connect to us. Note that all this logic is handled by the network
	event processor, we just provide a visual feedback to the user."""
	for i in self.downloads:
	    if i.req == req:
		i.status = _("Waiting for peer to connect")
                self.downloadspanel.update(i)
        for i in self.uploads:
            if i.req == req:
                i.status = _("Waiting for peer to connect")
                self.uploadspanel.update(i)

    def gotCantConnect(self,req):
	""" We can't connect to the user, either way. """
	for i in self.downloads:
	    if i.req == req:
		i.status = _("Cannot connect")
		i.req = None
                self.downloadspanel.update(i)
		self.queue.put(slskmessages.GetUserStatus(i.user))
        for i in self.uploads:
            if i.req == req:
                i.status = _("Cannot connect")
		i.req = None
		curtime = time.time()
                for j in self.uploads:
                    if j.user == i.user:
                        j.timequeued = curtime
                self.uploadspanel.update(i)
		self.queue.put(slskmessages.GetUserStatus(i.user))
		self.checkUploadQueue()


    def gotFileConnect(self, req, conn):
	""" A transfer connection has been established, 
	now exchange initialisation messages."""
	for i in self.downloads:
	    if i.req == req:
		i.status = _("Initializing transfer")
		self.downloadspanel.update(i)
	for i in self.uploads:
            if i.req == req:
                i.status = _("Initializing transfer")
                self.uploadspanel.update(i)

    def gotConnect(self, req, conn):
	""" A connection has been established, now exchange initialisation
	messages."""
	for i in self.downloads:
	    if i.req == req:
		i.status = _("Requesting file")
		i.requestconn = conn
		self.downloadspanel.update(i)
	for i in self.uploads:
            if i.req == req:
                i.status = _("Requesting file")
		i.requestconn = conn
                self.uploadspanel.update(i)


    def TransferRequest(self,msg):
    	user = None
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
	    self.eventprocessor.logMessage(_("Got transfer request %s but cannot determine requestor") % vars(msg),1)
	    return
	
	if msg.direction == 1:
	    for i in self.downloads:
		if i.filename == msg.file and user == i.user and i.status == "Queued":
		    i.size = msg.filesize
		    i.req = msg.req
		    i.status = _("Waiting for download")
		    transfertimeout = TransferTimeout(i.req, self.eventprocessor.frame.callback)
		    if i.transfertimer is not None:
			i.transfertimer.cancel()
		    i.transfertimer = threading.Timer(30.0, transfertimeout.timeout)
		    i.transfertimer.start()
		    response = slskmessages.TransferResponse(conn,1,req = i.req)
                    self.downloadspanel.update(i)
		    break
	    else:
		# Remote Uploads only for users in list (Added by daelstorm)
		if user in [i[0] for i in self.eventprocessor.userlist.userlist] and self.eventprocessor.config.sections["transfers"]["remotedownloads"] == 1:
			transfer = Transfer(user = user, filename=msg.file , path="", status = _('Getting status'))
			self.downloads.append(transfer)
                	self.SaveDownloads()
			self.queue.put(slskmessages.GetUserStatus(user))
			transfer.req = newId()
	    		self.downloadspanel.update(transfer)
			return
			
		else:
			response = slskmessages.TransferResponse(conn,0,reason = "Cancelled", req = msg.req)
			self.eventprocessor.logMessage(_("Denied file request: %s") % str(vars(msg)),1)
	else:
	    friend = user in [i[0] for i in self.eventprocessor.userlist.userlist]
	    if friend and self.eventprocessor.config.sections["transfers"]["friendsnolimits"]:
	        limits = 0
	    else:
	        limits = 1

	    checkuser, reason = self.eventprocessor.CheckUser(user, self.geoip, addr)
	    if not checkuser:
	        response = slskmessages.TransferResponse(conn,0,reason = reason, req=msg.req)
    	    elif not self.fileIsShared(user, msg.file):
		response = slskmessages.TransferResponse(conn,0,reason = "File not shared", req = msg.req)
	    elif self.fileIsQueued(user, msg.file):
		response = slskmessages.TransferResponse(conn,0,reason = "Queued", req = msg.req)
	    elif limits and self.queueLimitReached(user):
	        uploadslimit = self.eventprocessor.config.sections["transfers"]["queuelimit"]
		response = slskmessages.TransferResponse(conn,0,reason = _("User limit of %i megabytes exceeded") %(uploadslimit), req = msg.req)
	    elif user in self.getTransferringUsers() or self.bandwidthLimitReached() or self.transferNegotiating():
		response = slskmessages.TransferResponse(conn,0,reason = "Queued", req = msg.req)
		self.uploads.append(Transfer(user = user, filename = msg.file, path = os.path.dirname(msg.file.replace('\\',os.sep)), status = _("Queued"), timequeued = time.time(), size = self.getFileSize(msg.file)))
		self.uploadspanel.update(self.uploads[-1])
		self.addQueued(user, msg.file)
	    else:
		size = self.getFileSize(msg.file)
		response = slskmessages.TransferResponse(conn,1,req = msg.req, filesize = size)
                transfertimeout = TransferTimeout(msg.req, self.eventprocessor.frame.callback) 
		self.uploads.append(Transfer(user = user, filename = msg.file, path = os.path.dirname(msg.file.replace('\\',os.sep)), status = _("Waiting for upload"), req = msg.req, size = size))
                self.uploads[-1].transfertimer = threading.Timer(30.0, transfertimeout.timeout)
		self.uploads[-1].transfertimer.start()
		self.uploadspanel.update(self.uploads[-1])
	    self.eventprocessor.logMessage(_("Upload request: %s") % str(vars(msg)),1)

        if msg.conn is not None:
            self.queue.put(response)
        else:
            self.eventprocessor.ProcessRequestToPeer(user,response)

    def fileIsQueued(self, user, file):
	for i in self.uploads:
            if i.user == user and i.filename == file and i.status == "Queued":
		return 1
	return 0

    def queueLimitReached(self, user):
	uploadslimit = self.eventprocessor.config.sections["transfers"]["queuelimit"]*1024*1024
	sizelist = [i.size for i in self.uploads if i.user == user and i.status == 'Queued']
	size = reduce(lambda x, y: x+y, sizelist, 0)
	return size >= uploadslimit

    def QueueUpload(self, msg):
        user = None
        for i in self.peerconns:
            if i.conn is msg.conn.conn:
                user = i.username
        if user is None:
            return
        addr = msg.conn.addr[0]
	if not self.fileIsQueued(user, msg.file):
	    friend = user in [i[0] for i in self.eventprocessor.userlist.userlist]
	    if friend and self.eventprocessor.config.sections["transfers"]["friendsnolimits"]:
	        limits = 0
	    else:
	        limits = 1
	    
	    checkuser, reason = self.eventprocessor.CheckUser(user, self.geoip, addr)
	    if not checkuser:
		self.queue.put(slskmessages.QueueFailed(conn = msg.conn.conn, file = msg.file, reason = reason))
            elif limits and self.queueLimitReached(user):
                uploadslimit = self.eventprocessor.config.sections["transfers"]["queuelimit"]
		limitmsg = _("User limit of %i megabytes exceeded") %(uploadslimit)
                self.queue.put(slskmessages.QueueFailed(conn = msg.conn.conn, file = msg.file, reason = limitmsg)) 
 	    elif self.fileIsShared(user, msg.file):
	        self.uploads.append(Transfer(user = user, filename = msg.file, path = os.path.dirname(msg.file.replace('\\',os.sep)), status = "Queued", timequeued = time.time(), size = self.getFileSize(msg.file)))
		self.uploadspanel.update(self.uploads[-1])
		self.addQueued(user, msg.file)
	    else:
		self.queue.put(slskmessages.QueueFailed(conn = msg.conn.conn, file = msg.file, reason = _("File not shared") ))
        self.eventprocessor.logMessage(_("Queued upload request: %s") % str(vars(msg)),1)
	self.checkUploadQueue()


    def QueueFailed(self, msg):
        for i in self.peerconns:
            if i.conn is msg.conn.conn:
                user = i.username
        for i in self.downloads:
            if i.user == user and i.filename == msg.file and i.status == 'Queued':
		i.status = msg.reason
		self.downloadspanel.update(i)
                break


    def fileIsShared(self, user, filename):
	filename = filename.replace("\\",os.sep)
	if not os.access(filename, os.R_OK): return 0
	dir = os.path.dirname(filename)
	file = os.path.basename(filename)
	if self.eventprocessor.config.sections["transfers"]["enablebuddyshares"]:
		if user in [i[0] for i in self.eventprocessor.config.sections["server"]["userlist"]]:
			bshared = self.eventprocessor.config.sections["transfers"]["bsharedfiles"]
			for i in bshared.get(dir, ''):
				if file == i[0]: return 1
	shared = self.eventprocessor.config.sections["transfers"]["sharedfiles"]
	for i in shared.get(dir, ''):
		if file == i[0]:
			return 1
	return 0

    def getTransferringUsers(self):
	return [i.user for i in self.uploads if i.req is not None or i.conn is not None or i.status == _('Getting status')] #some file is being transfered

    def transferNegotiating(self):
	return len([i for i in self.uploads if i.req is not None or (i.conn is not None and i.speed is None) or i.status == _('Getting status')]) > 0 #some file is being negotiated

    def bandwidthLimitReached(self):
	maxbandwidth = self.eventprocessor.config.sections["transfers"]["uploadbandwidth"]
	maxupslots = self.eventprocessor.config.sections["transfers"]["uploadslots"]
	useupslots = self.eventprocessor.config.sections["transfers"]["useupslots"]
	bandwidthlist = [i.speed for i in self.uploads if i.conn is not None and i.speed is not None]
	slotsreached = len(bandwidthlist) >= maxupslots
	return (reduce(lambda x, y: x+y, bandwidthlist, 0) > maxbandwidth) or (useupslots and slotsreached)

    def getFileSize(self,filename):
	try:
	    size = os.path.getsize(filename.replace("\\",os.sep))
	except:
	    size = 0
	return size

    def TransferResponse(self,msg):
	""" Got a response to the file request from the peer."""
	if msg.reason != None:
	    for i in (self.downloads+self.uploads)[:]:
		if i.req == msg.req:
		    i.status = msg.reason
		    i.req = None
		    self.downloadspanel.update(i)
		    self.uploadspanel.update(i)
		    if msg.reason == "Queued":
			if i.user not in self.users or self.users[i.user].status is None:
		            self.queue.put(slskmessages.GetUserStatus(i.user))
		        if i in self.uploads:
			    if i.transfertimer is not None:
				i.transfertimer.cancel()
			    self.uploads.remove(i)
			    self.uploadspanel.update()
		    self.checkUploadQueue()
	elif msg.filesize != None:
	    for i in self.downloads:
		if i.req == msg.req:
                    i.size = msg.filesize
                    i.status = _("Establishing connection")
                    #Have to establish 'F' connection here
                    self.eventprocessor.ProcessRequestToPeer(i.user,slskmessages.FileRequest(None,msg.req))
		    self.downloadspanel.update(i)
		    break
	else:
	    for i in self.uploads:
		if i.req == msg.req:
		    i.status = _("Establishing connection")
 		    self.eventprocessor.ProcessRequestToPeer(i.user,slskmessages.FileRequest(None,msg.req))
		    self.uploadspanel.update(i)
		    break
	    else:
		self.eventprocessor.logMessage(_("Got unknown transfer response: %s") % str(vars(msg)),1)

    def TransferTimeout(self, msg):
        for i in (self.downloads+self.uploads)[:]:
            if i.req == msg.req:
                i.status = _("Cannot connect")
                i.req = None
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
                        incompletedir = i.path
                    else:
                        incompletedir = os.path.join(downloaddir, i.path)
		try:
		    if not os.access(incompletedir,os.F_OK):
		        os.makedirs(incompletedir)
		except OSError, strerror:
		    self.eventprocessor.logMessage(_("OS error: %s") % strerror)
		    i.status = _("Download directory error")
		    i.conn = None
		    self.queue.put(slskmessages.ConnClose(msg.conn))
		else: 
                  # also check for a windows-style incomplete transfer
		  basename = string.split(i.filename,'\\')[-1]
		  basename = self.encode(basename, i.user)
                  winfname = os.path.join(incompletedir,"INCOMPLETE~"+basename)
                  pyfname  = os.path.join(incompletedir,"INCOMPLETE"+basename)
		  pynewfname = os.path.join(incompletedir,"INCOMPLETE"+md5.new(i.filename+i.user).hexdigest()+basename)
		  try:
                    if os.access(winfname,os.F_OK):
                        fname = winfname
                    elif os.access(pyfname,os.F_OK):
                        fname = pyfname
		    else:
			fname = pynewfname
                    f = open(fname,'ab+')
                  except IOError, strerror:
                    self.eventprocessor.logMessage(_("I/O error: %s") % strerror)
                    i.status = _("Local file error")
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
                    f.seek(0,2)
		    size = f.tell()
		    self.queue.put(slskmessages.DownloadFile(i.conn,size,f,i.size))
		    i.currentbytes = size
                    i.status = "%s" %(str(i.currentbytes))
                    i.file = f
		    i.offset = size
		    i.starttime = time.time()
		    self.eventprocessor.logMessage(_("Download started: %s") % self.decode(f.name))
		    self.eventprocessor.logTransfer(_("Download started: user %s, file %s") % (i.user, self.decode(i.filename)))

                self.downloadspanel.update(i)
		return
         
	for i in self.uploads:
            if msg.req == i.req and i.conn is None:
                i.conn = msg.conn
		i.req = None
                if i.transfertimer is not None:
                    i.transfertimer.cancel()
                try:
		    f = open(i.filename.replace("\\",os.sep),"rb")
		    self.queue.put(slskmessages.UploadFile(i.conn,file = f,size = i.size))
		    i.status = _("Initializing transfer")
		    i.file = f
		    self.eventprocessor.logTransfer(_("Upload started: user %s, file %s") % (i.user, self.decode(i.filename)))
                except IOError, strerror:
		    self.eventprocessor.logMessage(_("I/O error: %s") % strerror)
                    i.status = _("Local file error")
                    try:
                        f.close()
                    except:
                        pass
                    i.conn = None
                    self.queue.put(slskmessages.ConnClose(msg.conn))
                self.uploadspanel.update(i)
                break
	else:
	    self.eventprocessor.logMessage(_("Unknown file request: %s") % str(vars(msg)),1)
	    self.queue.put(slskmessages.ConnClose(msg.conn))

    def FileDownload(self, msg):
	""" A file download is in progress"""
	needupdate = 1

	for i in self.downloads:
	    if i.conn == msg.conn:
		    try:
			curtime = time.time()
                        i.currentbytes = msg.file.tell()
                        i.status = "%s" %(str(i.currentbytes))
			oldelapsed = i.timeelapsed
	                i.timeelapsed = self.getTime(curtime - i.starttime)
			if curtime > i.starttime and i.currentbytes > i.offset:
			    i.speed = (i.currentbytes - i.offset)/(curtime - i.starttime)/1024
	                    i.timeleft = self.getTime((i.size - i.currentbytes)/i.speed/1024)
		        if i.size > i.currentbytes:
			    if oldelapsed == i.timeelapsed:
				needupdate = 0
			    i.status = str(i.currentbytes)
			else:
		            msg.file.close()
			    basename = self.encode(string.split(i.filename,'\\')[-1], i.user)
			    downloaddir = self.eventprocessor.config.sections["transfers"]["downloaddir"]
			    if i.path and i.path[0] == '/':
			        folder = i.path
			    else:
			        folder = os.path.join(downloaddir, self.encode(i.path))
		            if not os.access(folder,os.F_OK):
			        os.makedirs(folder)
			    newname = self.getRenamed(os.path.join(folder, basename))
			    try:
		                os.rename(msg.file.name,newname)
		            except OSError:
		                try:
		                    f1 = open(msg.file.name, "r")
		                    d = f1.read()
		                    f1 = open(newname, "w")
		                    f1.write(d)
		                    f1.close()
		                    os.remove(msg.file.name)
		                except OSError:
		                    self.eventprocessor.logMessage(_("Couldn't move '%s' to '%s'") % (self.decode(msg.file.name), self.decode(newname)))
		            i.status = _("Finished")
			    self.eventprocessor.logMessage(_("Download finished: %s") % self.decode(newname))
			    self.eventprocessor.logTransfer(_("Download finished: user %s, file %s") % (i.user, self.decode(i.filename)))
			    self.queue.put(slskmessages.ConnClose(msg.conn))
			    if i.speed is not None:
			        self.queue.put(slskmessages.SendSpeed(i.user, int(i.speed*1024)))
			    i.conn = None
			    self.addToShared(newname)
			    self.eventprocessor.sendNumSharedFoldersFiles()
			    self.SaveDownloads()
			    self.downloadspanel.update(i)
			    if self.eventprocessor.config.sections["transfers"]["afterfinish"]:
			        command = self.eventprocessor.config.sections["transfers"]["afterfinish"].replace("$", utils.escapeCommand(newname))
			        os.system(command)
			        self.eventprocessor.logMessage(_("Executed: %s") % self.decode(command))
			    if self.eventprocessor.config.sections["transfers"]["afterfolder"] and i.path:
			        # walk through downloads and break if any file in the same folder exists, else execute
			        for ia in self.downloads:
			            if ia.status not in [_('Finished'),_('Aborted')] and ia.path and ia.path == i.path:
			                break
			        else:
			            command = self.eventprocessor.config.sections["transfers"]["afterfolder"].replace("$", utils.escapeCommand(folder))
			            os.system(command)
			            self.eventprocessor.logMessage(_("Executed on folder: %s") % self.decode(command))
		    except IOError, strerror:
			self.eventprocessor.logMessage(_("I/O error: %s") % self.decode(strerror))
                        i.status = _("Local file error")
	                try:
	                    msg.file.close()
	                except:
	                    pass
	                i.conn = None
	                self.queue.put(slskmessages.ConnClose(msg.conn))
		    if needupdate:
		        self.downloadspanel.update(i)
    
    def addToShared(self, name):
	prefix = ""
	prefix2 = ""
	if self.eventprocessor.config.sections["transfers"]["enablebuddyshares"] and self.eventprocessor.config.sections["transfers"]["friendsonly"]:
		prefix = "b"
		prefix2 = "buddy"
		
		
	if self.eventprocessor.config.sections["transfers"]["sharedownloaddir"]:
	    shared = self.eventprocessor.config.sections["transfers"][prefix+"sharedfiles"]
	    sharedstreams = self.eventprocessor.config.sections["transfers"][prefix+"sharedfilesstreams"]
	    wordindex = self.eventprocessor.config.sections["transfers"][prefix+"wordindex"]
	    fileindex = self.eventprocessor.config.sections["transfers"][prefix+"fileindex"]
	    shareddirs = self.eventprocessor.config.sections["transfers"][prefix2+"shared"] + [self.eventprocessor.config.sections["transfers"]["downloaddir"]]
	    sharedmtimes = self.eventprocessor.config.sections["transfers"][prefix+"sharedmtimes"]
            dir = os.path.dirname(name)
            file = os.path.basename(name)
	    size = os.path.getsize(name)

	    shared[dir] = shared.get(dir, [])
	    if file not in [i[0] for i in shared[dir]]:
		fileinfo = utils.getFileInfo(file,name)
		shared[dir] = shared[dir] + [fileinfo]
		sharedstreams[dir] = utils.getDirStream(shared[dir])
		words = utils.getIndexWords(dir,file, shareddirs)
		self.addToIndex(wordindex, fileindex, words, dir, fileinfo)
		sharedmtimes[dir] = os.path.getmtime(dir)
	        self.eventprocessor.config.writeShares()
		

    def addToIndex(self, wordindex, fileindex, words, dir, fileinfo):
	index = len(fileindex.keys())
	for i in words:
	    if not wordindex.has_key(i):
		wordindex[i] = [index]
	    else:
		wordindex[i] = wordindex[i] + [index]
	fileindex[str(index)] = (os.path.join(dir,fileinfo[0]),)+fileinfo[1:]

    def FileUpload(self,msg):
        """ A file upload is in progress"""
	needupdate = 1

        for i in self.uploads:
            if i.conn == msg.conn:
		curtime = time.time()
		if i.starttime is None:
		    i.starttime = curtime
		    i.offset = msg.offset
		i.currentbytes = msg.offset + msg.sentbytes
		oldelapsed = i.timeelapsed
		i.timeelapsed = self.getTime(curtime - i.starttime)
		if curtime > i.starttime and i.currentbytes > i.offset:
		    i.speed = (i.currentbytes - i.offset)/(curtime - i.starttime)/1024
		    i.timeleft = self.getTime((i.size - i.currentbytes)/i.speed/1024)
		    self.checkUploadQueue()
		if i.size > i.currentbytes:
		    if oldelapsed == i.timeelapsed:
			needupdate = 0
                    i.status = str(i.currentbytes)
		    
                    if i.user in self.privilegedusers:
			    i.modifier = _("(privileged)")
		    elif self.UserListPrivileged(i.user):
			    i.modifier = _("(friend)")
		else:
                    msg.file.close()
                    i.status = _("Finished")
#                    i.conn = None
#		    self.queue.put(slskmessages.ConnClose(msg.conn))
		    for j in self.uploads:
			if j.user == i.user:
			    j.timequeued = curtime
		    self.eventprocessor.logTransfer(_("Upload finished: user %s, file %s") % (i.user, self.decode(i.filename)))
		    self.checkUploadQueue()
		    self.uploadspanel.update(i)
		if needupdate:
                    self.uploadspanel.update(i)

    def BanUser(self, user):
        if self.eventprocessor.config.sections["transfers"]["usecustomban"]:
            banmsg = _("Banned (%s)") % self.eventprocessor.config.sections["transfers"]["customban"]
        else:
            banmsg = _("Banned")

    	list = [i for i in self.uploads if i.user == user]
        for upload in list:
	    if upload.status == "Queued":
		self.eventprocessor.ProcessRequestToPeer(user,slskmessages.QueueFailed(None,file = upload.filename, reason = banmsg))
	    else:
                self.AbortTransfer(upload)
        if self.uploadspanel is not None:
	    self.uploadspanel.ClearByUser(user)
        if user not in self.eventprocessor.config.sections["server"]["banlist"]:
            self.eventprocessor.config.sections["server"]["banlist"].append(user)
            self.eventprocessor.config.writeConfig()


    def checkUploadQueue(self):
	if self.bandwidthLimitReached() or self.transferNegotiating():
	    return
	transfercandidate = None
	trusers = self.getTransferringUsers()
	list = [i for i in self.uploads if not i.user in trusers and i.status == "Queued"]
	listogg = [i for i in list if i.filename[-4:].lower() == ".ogg"]
	listprivileged = [i for i in list if i.user in self.privilegedusers or self.UserListPrivileged(i.user)]
	if len(listogg) > 0:
	    list = listogg
	if len(listprivileged) > 0:
	    list = listprivileged
	if len(list) == 0:
	    return
	mintimequeued = time.time() + 1
	for i in list:
	    if i.timequeued < mintimequeued:
		transfercandidate = i
		mintimequeued = i.timequeued
	if transfercandidate is not None:
	    self.pushFile(user = transfercandidate.user, filename = transfercandidate.filename, transfer = transfercandidate)
	    self.removeQueued(transfercandidate.user, transfercandidate.filename)

    def PlaceInQueueRequest(self, msg):
        for i in self.peerconns:
            if i.conn is msg.conn.conn:
                user = i.username
		
	list = {user:time.time()}
	listogg = {user:time.time()}
	listpriv = {user:time.time()}
	countogg = 0
	countpriv = 0
	
        for i in self.uploads:
	    if i.status == "Queued":
		if i.user in listpriv.keys() or i.user in self.privilegedusers or self.UserListPrivileged(i.user):
		    listpriv[i.user] = i.timequeued
		    countpriv += 1
		elif i.filename[-4:].lower() == ".ogg":
		    listogg[i.user] = i.timequeued
		    countogg += 1
		else:
		    list[i.user] = i.timequeued

	place = 0
	if user in self.privilegedusers or self.UserListPrivileged(user):
	    list = listpriv
	elif msg.file[-4:].lower() == ".ogg":
	    list = listogg
	    place = place + countpriv
	else:
	    place = place + countpriv + countogg
	for i in list.keys():
	    if list[i] < list[user]:
		place = place + 1
	self.queue.put(slskmessages.PlaceInQueue(msg.conn.conn, msg.file, place))

    def getTime(self,seconds):
	sec = int(seconds % 60)
	minutes = int(seconds / 60 % 60)
	hours = int(seconds / 3600 % 24)
	days = int(seconds/86400)
	
	time = "%02d:%02d:%02d" %(hours, minutes, sec)
	if days > 0:
	    time = str(days) + "." + time
	return time

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
	if username in self.privilegedusers or self.UserListPrivileged(username):
	    return len(self.privusersqueued), len(self.privusersqueued)
	else:
	    return len(self.usersqueued)+self.privcount+self.oggcount, len(self.oggusersqueued)+self.privcount

    def addQueued(self, user, filename):
        if user in self.privilegedusers:
            self.privusersqueued.setdefault(user,0)
            self.privusersqueued[user] += 1
            self.privcount += 1
        elif filename[-4:].lower() == ".ogg":
            self.oggusersqueued.setdefault(user,0)
            self.oggusersqueued[user] += 1
            self.oggcount += 1
        else:
            self.usersqueued.setdefault(user,0)
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
	if self.bandwidthLimitReached():
	    return len(list)
	else:
	    return len(list)+1
	    

    def UserListPrivileged(self, user):
        if self.eventprocessor.config.sections["transfers"]["preferfriends"]:
            return user in [i[0] for i in self.eventprocessor.config.sections["server"]["userlist"]]
	userlist = [i[0] for i in self.eventprocessor.config.sections["server"]["userlist"]]
	if user not in userlist:
	    return 0
	if self.eventprocessor.config.sections["server"]["userlist"][userlist.index(user)][3]:
	   return 1
	else:
	   return 0

    def ConnClose(self, conn, addr):
	""" The remote user has closed the connection either because
	he logged off, or because there's a network problem."""
	for i in self.downloads + self.uploads:
	    if i.requestconn == conn and i.status == _('Requesting file'):
		i.requestconn = None
		i.status = _("Connection closed by peer")
		i.req = None
                self.downloadspanel.update(i)
                self.uploadspanel.update(i)
                self.checkUploadQueue()
	    if i.conn == conn:
		if i.file is not None:
		    i.file.close()
		if i.status != _("Finished"):
		    if self.users.has_key(i.user) and self.users[i.user].status == 0:
		        i.status = _("User logged off")
		    else:
		        i.status = _("Connection closed by peer")
		        if i in self.downloads:
			    self.eventprocessor.logTransfer(_("Retrying failed download: user %s, file %s") %(i.user, self.decode(i.filename)), 1)
			    self.getFile(i.user, i.filename, i.path, i)
		i.conn = None
       	        self.downloadspanel.update(i)
	        self.uploadspanel.update(i)
	 	self.checkUploadQueue()

    def getRenamed(self,name):
	""" When a transfer is finished, we remove INCOMPLETE~ or INCOMPLETE 
	prefix from the file's name. """
	if not os.path.exists(name):
	    return name
	else:
	    n = 1
	    while n < 1000:
		newname = name+"."+str(n)
		if not os.path.exists(newname):
		    break
		n+=1
	return newname

    def PlaceInQueue(self,msg):
	""" The server tells us our place in queue for a particular transfer."""
	self.eventprocessor.logMessage(_("File: %s, place in queue: %s") % (self.decode(msg.filename.split('\\')[-1]), msg.place))

    def FileError(self, msg):
	""" Networking thread encountered a local file error"""
	for i in self.downloads+self.uploads:
	    if i.conn == msg.conn.conn:
		i.status = _("Local file error")
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


    def FolderContentsResponse(self,msg):
	""" When we got a contents of a folder, get all the files in it, but
	skip the files in subfolders"""
        for i in self.peerconns:
            if i.conn is msg.conn.conn:
                username = i.username

        for i in msg.list.keys():
            for j in msg.list[i].keys():
                if os.path.commonprefix([i,j]) == j:
                    for k in msg.list[i][j]:
			if j[-1] == '\\':
                            self.getFile(username, j + k[1], j.split('\\')[-2])
			else:
			    self.getFile(username, j + '\\' + k[1], j.split('\\')[-1])

    def AbortTransfers(self):
	""" Stop all transfers """
	for i in self.downloads+self.uploads:
	    if i.status != _("Finished"):
		self.AbortTransfer(i)
		i.status = "Old"
#                self.downloadspanel.update()
#                self.uploadspanel.update()


    def AbortTransfer(self,transfer, remove = 0):
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
	        self.eventprocessor.logTransfer(_("Upload aborted, user %s file %s") % (transfer.user, transfer.filename))
	    else:
	        self.eventprocessor.logTransfer(_("Download aborted, user %s file %s") % (transfer.user, transfer.filename))

    def GetDownloads(self):
	""" Get a list of incomplete and not aborted downloads """
	return [ [i.user, i.filename, i.path] for i in self.downloads if i.status != _('Finished')]

    def SaveDownloads(self):
	self.eventprocessor.config.sections["transfers"]["downloads"] = self.GetDownloads()
	self.eventprocessor.config.writeConfig()

    def decode(self, s):
        try:
            return s.decode(locale.nl_langinfo(locale.CODESET), "replace").encode("utf-8", "replace")
        except:
            return s

    def encode(self, s, user = None):
        coding = None
        if user and self.eventprocessor.config.sections["server"]["userencoding"].has_key(user):
            coding = self.eventprocessor.config.sections["server"]["userencoding"][user]
        s = self.eventprocessor.decode(s, coding)
        try:
            return s.encode(locale.nl_langinfo(locale.CODESET), "replace")
#            return s.sencode(os.filesystemencoding(), "replace")
        except:
            return s
