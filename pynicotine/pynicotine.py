# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
# Based on code from PySoulSeek, original copyright note:
# Copyright (c) 2001-2003 Alexander Kanavin. All rights reserved.

"""
This is the actual client code. Actual GUI classes are in the separate modules
"""

import time
import slskproto
import slskmessages
from slskmessages import newId
import transfers
import Queue
import threading
from config import *
import string
import types
import locale
from utils import _
import os

class PeerConnection:
    """
    Holds information about a peer connection. Not every field may be set
    to something. addr is (ip,port) address, conn is a socket object, msgs is
    a list of outgoing pending messages, token is a reverse-handshake 
    number (protocol feature), init is a PeerInit protocol message. (read
    slskmessages docstrings for explanation of these)
    """
    def __init__(self, addr = None, username = None, conn = None, msgs = None, token = None, init = None, conntimer = None, tryaddr = None):
	self.addr = addr
	self.username = username
	self.conn = conn
	self.msgs = msgs
	self.token = token
	self.init = init
	self.conntimer = conntimer
	self.tryaddr = tryaddr

class ConnectToPeerTimeout:
    def __init__(self, conn, callback):
	self.conn = conn
	self.callback = callback

    def timeout(self):
	self.callback([self])

class NetworkEventProcessor:
    """ This class contains handlers for various messages from the networking
    thread"""
    def __init__(self,frame,callback, writelog, setstatus, configfile):
#	self.searchfile = file("searches.txt","a")



	self.frame=frame
	self.callback = callback
	self.logMessage = writelog
	self.setStatus = setstatus

        self.config = Config(configfile)
        self.config.readConfig()

        self.queue = Queue.Queue(0)
        self.protothread = slskproto.SlskProtoThread(self.frame.networkcallback,self.queue,self.config.sections["server"]["portrange"])
	uselimit = self.config.sections["transfers"]["uselimit"]
	uploadlimit = self.config.sections["transfers"]["uploadlimit"]
	limitby = self.config.sections["transfers"]["limitby"]
	self.queue.put(slskmessages.SetUploadLimit(uselimit,uploadlimit,limitby))
	if self.config.sections["transfers"]["geoblock"]:
	    panic = self.config.sections["transfers"]["geopanic"]
	    cc = self.config.sections["transfers"]["geoblockcc"]
	    self.queue.put(slskmessages.SetGeoBlock([panic, cc]))
	else:
	    self.queue.put(slskmessages.SetGeoBlock(None))

        self.serverconn = None
        self.waitport = None
        self.peerconns = []
        self.users = {}
        self.chatrooms = None
        self.privatechat = None
        self.globallist = None
        self.userinfo = None
        self.userbrowse = None
        self.search = None
        self.transfers = None
	self.userlist = None

	self.servertimer = None
	self.servertimeout = -1

	self.distribcache = {}
	self.speed = 0
	self.translatepunctuation = string.maketrans(string.punctuation,string.join([' ' for i in string.punctuation],''))

	try:
	    import GeoIP
	    self.geoip = GeoIP.new(GeoIP.GEOIP_STANDARD)
	except ImportError:
	    try:
	        import _GeoIP
	        self.geoip = _GeoIP.new(_GeoIP.GEOIP_STANDARD)
	    except ImportError:
	        self.geoip = None

        self.events = {slskmessages.ConnectToServer:self.ConnectToServer,
			slskmessages.ConnectError:self.ConnectError,
			slskmessages.IncPort:self.IncPort,
			slskmessages.ServerConn:self.ServerConn,
			slskmessages.ConnClose:self.ConnClose,
			slskmessages.Login:self.Login,
			slskmessages.MessageUser:self.MessageUser,
			slskmessages.ExactFileSearch:self.ExactFileSearch,
			slskmessages.UserJoinedRoom:self.UserJoinedRoom,
			slskmessages.SayChatroom:self.SayChatRoom,
			slskmessages.JoinRoom:self.JoinRoom,
			slskmessages.UserLeftRoom:self.UserLeftRoom,
			slskmessages.QueuedDownloads:self.QueuedDownloads,
			slskmessages.GetPeerAddress:self.GetPeerAddress,
			slskmessages.OutConn:self.OutConn,
			slskmessages.UserInfoReply:self.UserInfoReply,
			slskmessages.UserInfoRequest:self.UserInfoRequest,
			slskmessages.PierceFireWall:self.PierceFireWall,
			slskmessages.CantConnectToPeer:self.CantConnectToPeer,
			slskmessages.PeerTransfer:self.PeerTransfer,
			slskmessages.SharedFileList:self.SharedFileList,
			slskmessages.GetSharedFileList:self.GetSharedFileList,
			slskmessages.FileSearchRequest:self.FileSearchRequest,
			slskmessages.FileSearchResult:self.FileSearchResult,
			slskmessages.ConnectToPeer:self.ConnectToPeer,
			slskmessages.GetUserStatus:self.GetUserStatus,
			slskmessages.GetUserStats:self.GetUserStats,
			slskmessages.Relogged:self.Relogged,
			slskmessages.PeerInit:self.PeerInit,
			slskmessages.DownloadFile:self.FileDownload,
			slskmessages.UploadFile:self.FileUpload,
			slskmessages.FileRequest:self.FileRequest,
			slskmessages.TransferRequest:self.TransferRequest,
			slskmessages.TransferResponse:self.TransferResponse,
			slskmessages.QueueUpload:self.QueueUpload,
			slskmessages.QueueFailed:self.QueueFailed,
			slskmessages.UploadFailed:self.UploadFailed,
			slskmessages.PlaceInQueue:self.PlaceInQueue,
		        slskmessages.FileError:self.FileError,
			slskmessages.FolderContentsResponse:self.FolderContentsResponse,
			slskmessages.FolderContentsRequest:self.FolderContentsRequest,
			slskmessages.RoomList:self.RoomList,
			slskmessages.LeaveRoom:self.LeaveRoom,
			slskmessages.GlobalUserList:self.GlobalUserList,
			slskmessages.AddUser:self.AddUser,
			slskmessages.PrivilegedUsers:self.PrivilegedUsers,
			slskmessages.AddToPrivileged:self.AddToPrivileged,
			slskmessages.CheckPrivileges:self.CheckPrivileges,
			slskmessages.ServerPing:self.Msg83,
			slskmessages.Msg83:self.Msg83,
			slskmessages.Msg84:self.Msg83,
			slskmessages.Msg85:self.Msg83,
			slskmessages.Msg12547:self.Msg12547,
			slskmessages.ParentInactivityTimeout:self.Msg83,
			slskmessages.SearchInactivityTimeout:self.Msg83,
			slskmessages.MinParentsInCache:self.Msg83,
			slskmessages.Msg89:self.Msg83,
			slskmessages.WishlistInterval:self.WishlistInterval,
			slskmessages.DistribAliveInterval:self.Msg83,
			slskmessages.AdminMessage:self.AdminMessage,
			slskmessages.TunneledMessage:self.TunneledMessage,
			slskmessages.IncConn:self.IncConn,
			slskmessages.PlaceholdUpload:self.PlaceholdUpload,
			slskmessages.PlaceInQueueRequest:self.PlaceInQueueRequest,
			slskmessages.UploadQueueNotification:self.UploadQueueNotification,
			slskmessages.SearchRequest:self.SearchRequest,
			slskmessages.FileSearch:self.SearchRequest,
			slskmessages.RoomSearch:self.SearchRequest,
			slskmessages.UserSearch:self.SearchRequest,
			slskmessages.NetInfo:self.NetInfo,
			slskmessages.DistribAlive:self.DistribAlive,
			slskmessages.DistribSearch:self.DistribSearch,
			ConnectToPeerTimeout:self.ConnectToPeerTimeout,
			transfers.TransferTimeout:self.TransferTimeout,
			slskmessages.RescanShares:self.RescanShares,
			slskmessages.RescanBuddyShares:self.RescanBuddyShares,
			slskmessages.Notify:self.Notify,
			slskmessages.GlobalRecommendations:self.GlobalRecommendations,
			slskmessages.Recommendations:self.Recommendations,
			slskmessages.ItemRecommendations:self.ItemRecommendations,
			slskmessages.SimilarUsers:self.SimilarUsers,
			slskmessages.ItemSimilarUsers:self.ItemSimilarUsers,
			slskmessages.RoomTickerState:self.RoomTickerState,
			slskmessages.RoomTickerAdd:self.RoomTickerAdd,
			slskmessages.RoomTickerRemove:self.RoomTickerRemove,
			}


    def ProcessRequestToPeer(self, user, message, window = None, address = None):
        """ 
        Sends message to a peer and possibly sets up a window to display 
        the result.
        """

        conn = None
        for i in self.peerconns:
            if i.username == user and i.init.type == 'P' and message.__class__ is not slskmessages.FileRequest:
                conn = i
                break
        if conn is not None:
            if conn.conn is not None:
                message.conn = conn.conn
                self.queue.put(message)
                if window is not None:
                    window.InitWindow(conn.username,conn.conn)
                if message.__class__ is slskmessages.TransferRequest and self.transfers is not None:
                    self.transfers.gotConnect(message.req,conn.conn)
		return
            else:
                conn.msgs.append(message)
        else:
            if message.__class__ is slskmessages.FileRequest:
                type = 'F'
	    elif message.__class__ is slskmessages.DistribConn:
		type = 'D'
            else:
                type = 'P'
            init = slskmessages.PeerInit(None,self.config.sections["server"]["login"],type,0)
            firewalled = self.config.sections["server"]["firewalled"]
	    addr = None
            behindfw = None
	    token = None
            if self.users.has_key(user):
                addr = self.users[user].addr
                behindfw = self.users[user].behindfw
            elif address is not None:
                addr = address
            if firewalled:
                if addr is None:
                    self.queue.put(slskmessages.GetPeerAddress(user))
                elif behindfw is None:
                    self.queue.put(slskmessages.OutConn(None,addr))
                else:
                    firewalled = 0
            if not firewalled:
                token = newId()
                self.queue.put(slskmessages.ConnectToPeer(token,user,type))
	    conn = PeerConnection(addr = addr, username = user, msgs = [message], token = token, init = init)
            self.peerconns.append(conn)
	    if token is not None:
		conntimeout = ConnectToPeerTimeout(self.peerconns[-1],self.frame.callback)
		timer = threading.Timer(300.0, conntimeout.timeout)
		self.peerconns[-1].conntimer = timer
		timer.start()
	if message.__class__ is slskmessages.TransferRequest and self.transfers is not None:
	    if conn.addr is None:
		self.transfers.gettingAddress(message.req)
	    elif conn.token is None:
		self.transfers.gotAddress(message.req)
	    else:
		self.transfers.gotConnectError(message.req)

    def setServerTimer(self):
        if self.servertimeout == -1:
            self.servertimeout = 15
        elif 0 < self.servertimeout < 3600:
            self.servertimeout = self.servertimeout * 2
        self.servertimer = threading.Timer(self.servertimeout, self.ServerTimeout)
	self.servertimer.start()
        self.logMessage(_("The server seems to be down or not responding, retrying in %i seconds") %(self.servertimeout))

    def ServerTimeout(self):
        if not self.config.needConfig():
            self.frame.callback([slskmessages.ConnectToServer()])

    def StopTimers(self):
	for i in self.peerconns:
	    if i.conntimer is not None:
		i.conntimer.cancel()

    def ConnectToServer(self, msg):
        self.frame.OnConnect(None)

    def encode(self, str, networkenc = None):
        if networkenc is None:
	    networkenc = self.config.sections["server"]["enc"]
	if type(str) is types.UnicodeType:
	    return str.encode(networkenc,'replace')
	else:
	    return str.decode("utf-8",'replace').encode(networkenc,'replace')

    def decode(self, string, networkenc = None):
    	if networkenc is None:
	    networkenc = self.config.sections["server"]["enc"]
	return str(string).decode(networkenc,'replace').encode("utf-8", "replace")

    def getencodings(self):
	return [["Latin", 'ascii'], ["US-Canada", 'cp037'],  ['Hebrew', 'cp424'], ['US English', 'cp437'], ['International', 'cp500'], ['Greek', 'cp737'], ['Estonian', 'cp775'], ['Western European', 'cp850'], ['Central European', 'cp852'], ['Cyrillic', 'cp855'], ['Cyrillic', 'cp856'], ['Turkish', 'cp857'], ['Portuguese', 'cp860'], ['Icelandic', 'cp861'], ['Hebrew', 'cp862'], ['French Canadian', 'cp863'], ['Arabic', 'cp864'], ['Nordic', 'cp865'], ['Cyrillic', 'cp866'], ['Latin-9', 'cp869'], ['Thai', 'cp874'], ['Greek', 'cp875'], ['Japanese', 'cp932'], ['Chinese Simple', 'cp936'], ['Korean', 'cp949'], ['Chinese Traditional', 'cp950'], ['Urdu',  'cp1006'], ['Turkish',  'cp1026'], ['Latin', 'cp1140'], ['Central European', 'cp1250'], ['Cyrillic', 'cp1251'], ['Latin', 'cp1252'], ['Greek', 'cp1253'], ['Turkish', 'cp1254'], ['Hebrew', 'cp1255'], ['Arabic', 'cp1256'], ['Baltic', 'cp1257'], ['Vietnamese', 'cp1258'],  ['Latin', 'iso8859-1'], ['Latin 2', 'iso8859-2'], ['South European', 'iso8859-3'], ['North European', 'iso8859-4'], ['Cyrillic', 'iso8859-5'], ['Arabic', 'iso8859-6'], ['Greek', 'iso8859-7'], ['Hebrew', 'iso8859-8'], ['Turkish', 'iso8859-9'], ['Nordic', 'iso8859-10'], ['Thai', 'iso8859-11'], ['Baltic', 'iso8859-13'], ['Celtic', 'iso8859-14'], ['Western European', 'iso8859-15'], ['South-Eastern European', 'iso8859-16'], ['Cyrillic', 'koi8-r'], ['Latin', 'latin-1'], ['Cyrillic', 'mac-cyrillic'], ['Greek', 'mac-greek'], ['Icelandic', 'mac-iceland'], ['Latin 2', 'mac-latin2'], ['Latin', 'mac-roman'], ['Turkish', 'mac-turkish'], ['International', 'utf-16'], ['International', 'utf-7'], ['International', 'utf-8']]

    def sendNumSharedFoldersFiles(self):
	conf = self.config.sections
	
	if conf["transfers"]["enablebuddyshares"] and conf["transfers"]["friendsonly"]:
		shared_db = "bsharedfiles"
	else:
		shared_db = "sharedfiles"
        sharedfolders = len(conf["transfers"][shared_db].keys())
        sharedfiles = 0
        for i in conf["transfers"][shared_db].keys():
            sharedfiles = sharedfiles + len(conf["transfers"][shared_db][i])
        self.queue.put(slskmessages.SharedFoldersFiles(sharedfolders,sharedfiles))

    def RescanShares(self,msg):
	import utils
	utils.frame = self.frame
	utils.log = self.logMessage
        files, streams, wordindex, fileindex, mtimes = utils.rescandirs(msg.shared,self.config.sections["transfers"]["sharedmtimes"],self.config.sections["transfers"]["sharedfiles"],self.config.sections["transfers"]["sharedfilesstreams"],msg.yieldfunction)
	self.frame.RescanFinished([files, streams, wordindex, fileindex, mtimes], "normal")
	
    def RescanBuddyShares(self,msg):
	import utils
	utils.frame = self.frame
	utils.log = self.logMessage
        files, streams, wordindex, fileindex, mtimes = utils.rescandirs(msg.shared,self.config.sections["transfers"]["bsharedmtimes"],self.config.sections["transfers"]["bsharedfiles"],self.config.sections["transfers"]["bsharedfilesstreams"],msg.yieldfunction)
	self.frame.RescanFinished([files, streams, wordindex, fileindex, mtimes], "buddy")
	
    def Notify(self, msg):
	self.logMessage("%s" % self.decode(msg.msg))

    def ConnectError(self,msg):
	if msg.connobj.__class__ is slskmessages.ServerConn:
	    self.setStatus(_("Can't connect to server %s:%s: %s") % (msg.connobj.addr[0],msg.connobj.addr[1],self.decode(msg.err)))
	    self.setServerTimer()
	    if self.serverconn is not None:
	        self.serverconn = None

	    self.frame.ConnectError(msg)
	elif msg.connobj.__class__ is slskmessages.OutConn:
            for i in self.peerconns[:]:
                if i.addr == msg.connobj.addr and i.conn is None: 
		    if i.token is None:
		        i.token  = newId()
		        self.queue.put(slskmessages.ConnectToPeer(i.token,i.username,i.init.type))
			if self.users.has_key(i.username):
		            self.users[i.username].behindfw = "yes"
	                for j in i.msgs: 
	                    if j.__class__ is slskmessages.TransferRequest and self.transfers is not None:
			       self.transfers.gotConnectError(j.req)
                	conntimeout = ConnectToPeerTimeout(i,self.frame.callback)
                	timer = threading.Timer(300.0, conntimeout.timeout)
			timer.start()
			if i.conntimer is not None:
			    i.conntimer.cancel()
                	i.conntimer = timer
		    else:
                        for j in i.msgs:
			    if j.__class__ in [slskmessages.TransferRequest,slskmessages.FileRequest] and self.transfers is not None:
                               self.transfers.gotCantConnect(j.req)
			self.logMessage(_("Can't connect to %s, sending notification via the server") %(i.username),1)
			self.queue.put(slskmessages.CantConnectToPeer(i.token,i.username))
			if i.conntimer is not None:
			    i.conntimer.cancel()
			self.peerconns.remove(i)
		    break
	    else:
	        self.logMessage("%s %s %s" %(msg.err, msg.__class__, vars(msg)))
	else:
	    self.logMessage("%s %s %s" %(msg.err, msg.__class__, vars(msg)),1)
	    self.ClosedConnection(msg.connobj.conn, msg.connobj.addr)

    def IncPort(self, msg):
        self.waitport = msg.port
	self.setStatus(_("Listening on port %i") %(msg.port))

    def ServerConn(self, msg):
	self.setStatus(_("Connected to server %s:%s, logging in...") %(msg.addr[0],msg.addr[1]))
	time.sleep(1)
	self.serverconn = msg.conn
	self.servertimeout = -1
	self.users = {}
	self.queue.put(slskmessages.Login(self.config.sections["server"]["login"],self.config.sections["server"]["passw"],181))
        if self.waitport is not None:	
	    self.queue.put(slskmessages.SetWaitPort(self.waitport))

    def PeerInit(self, msg):
#	list = [i for i in self.peerconns if i.conn == msg.conn.conn]
#	if list == []:
	    self.peerconns.append(PeerConnection(addr = msg.conn.addr, username = msg.user, conn = msg.conn.conn, init = msg, msgs = []))
#	else:
#	    for i in list:
#		i.init = msg
#		i.username = msg.user

    def ConnClose(self, msg):
       self.ClosedConnection(msg.conn, msg.addr)

    def ClosedConnection(self, conn, addr):
	if conn == self.serverconn:
	    self.setStatus(_("Disconnected from server %s:%s") %(addr[0],addr[1]))
	    if not self.frame.manualdisconnect:
		self.setServerTimer()
	    else:
		self.frame.manualdisconnect = 0
	    self.serverconn = None
	    if self.transfers is not None:
		self.transfers.AbortTransfers()
	    self.privatechat = self.chatrooms = self.userinfo = self.userbrowse = self.search = self.transfers = self.userlist = None
	    self.frame.ConnClose(conn, addr)
        else:
	    for i in self.peerconns[:]:
	        if i.conn == conn:
		    self.logMessage(_("Connection closed by peer: %s") % self.decode(vars(i)),1)
		    if i.conntimer is not None:
			i.conntimer.cancel()
		    if self.transfers is not None:
			self.transfers.ConnClose(conn, addr)
		    if i == self.GetDistribConn():
			self.DistribConnClosed(i)
   		    self.peerconns.remove(i)
		    break
	    else:
		self.logMessage(_("Removed connection closed by peer: %s %s") %(conn, addr),1)
	
    def Login(self,msg):
	self.logintime = time.time()
	conf = self.config.sections
	if msg.success:
	    self.setStatus(_("Logged in, getting the list of rooms..."))
	    self.transfers = transfers.Transfers(conf["transfers"]["downloads"],self.peerconns,self.queue, self, self.users)

	    self.privatechat, self.chatrooms, self.userinfo, self.userbrowse, self.search, downloads, uploads, self.userlist = self.frame.InitInterface(msg)

	    self.transfers.setTransferPanels(downloads, uploads)
	    self.sendNumSharedFoldersFiles()
	    self.queue.put(slskmessages.SetStatus((not self.frame.away)+1))
	    for thing in self.config.sections["interests"]["likes"]:
                self.queue.put(slskmessages.AddThingILike(self.encode(thing)))
	    for thing in self.config.sections["interests"]["dislikes"]:
                self.queue.put(slskmessages.AddThingIHate(self.encode(thing)))
	    self.privatechat.Login()
	else:
	    self.frame.manualdisconnect = 1
	    self.setStatus(_("Can not log in, reason: %s") %(msg.reason))
	    self.logMessage(_("Can not log in, reason: %s") %(msg.reason))


    def MessageUser(self, msg):
	status = 0
	if time.time() <= self.logintime + 2:
		# Offline message 
		status = 1
		
	if self.privatechat is not None:
	    self.privatechat.ShowMessage(msg,msg.msg,status=status)
	    self.queue.put(slskmessages.MessageAcked(msg.msgid))
       	else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))

    def UserJoinedRoom(self,msg):
	if self.chatrooms is not None:
	    self.chatrooms.roomsctrl.UserJoinedRoom(msg)
	else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))


    def JoinRoom(self,msg):
	if self.chatrooms is not None:
            self.chatrooms.roomsctrl.JoinRoom(msg)
            ticker = ""
            if self.config.sections["ticker"]["rooms"].has_key(msg.room):
                ticker = self.config.sections["ticker"]["rooms"][msg.room]
            elif self.config.sections["ticker"]["default"]:
                ticker = self.config.sections["ticker"]["default"]
            if ticker:
                encoding = self.config.sections["server"]["enc"]
                if self.config.sections["server"]["roomencoding"].has_key(msg.room):
                  encoding = self.config.sections["server"]["roomencoding"][msg.room]
                self.queue.put(slskmessages.RoomTickerSet(msg.room, self.encode(ticker, encoding)))
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))

    def LeaveRoom(self,msg):
        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.LeaveRoom(msg)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))


    def SayChatRoom(self,msg):
        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.SayChatRoom(msg,msg.msg)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))

    def AddUser(self,msg):
        if self.transfers is not None:
            self.transfers.getAddUser(msg)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))

    def PrivilegedUsers(self,msg):
        if self.transfers is not None:
            self.transfers.setPrivilegedUsers(msg.users)
	    self.logMessage(_("%i privileged users") %(len(msg.users)))
	    self.queue.put(slskmessages.HaveNoParent(1))
	    self.queue.put(slskmessages.GetUserStats(self.config.sections["server"]["login"]))
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))

    def AddToPrivileged(self, msg):
	if self.transfers is not None:
            self.transfers.addToPrivileged(msg.user)
	    self.logMessage(_("User %s added to privileged list") %(msg.user),1)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))

    def CheckPrivileges(self, msg):
        mins = msg.days / 60
        hours = mins / 60
        days = hours / 24
	self.logMessage(_("%i days, %i hours, %i minutes, %i seconds of download privileges left") %(days, hours % 24, mins % 60, msg.days % 60))

    def AdminMessage(self, msg):
	self.logMessage("%s" %(msg.msg))

    def Msg83(self, msg):
	self.logMessage("%s %s" %(msg.__class__, vars(msg)),1)
	
    def Msg12547(self, msg):
	self.logMessage("%s %s" %(msg.__class__, vars(msg)),1)

    def WishlistInterval(self, msg):
	if self.search is not None:
	    self.search.SetInterval(msg)
        else:
	    self.logMessage("%s %s" %(msg.__class__, vars(msg)),1)

    def GetUserStatus(self,msg):
	self.queue.put(slskmessages.AddUser(msg.user))
	if self.users.has_key(msg.user):
	    if msg.status == 0:
	        self.users[msg.user] = UserAddr(status = msg.status)
	    else:
	        self.users[msg.user].status = msg.status
	else:
	    self.users[msg.user] = UserAddr(status = msg.status)
	    
	if msg.privileged != None:
		if msg.privileged == 1:
			if self.transfers is not None:
				self.transfers.addToPrivileged(msg.user)
				self.logMessage(_("User %s added to privileged list") %(msg.user),1)
			else:
				self.logMessage("%s %s" %(msg.__class__, vars(msg)))

        self.frame.GetUserStatus(msg)
	if self.userlist is not None:
	    self.userlist.GetUserStatus(msg)
	if self.transfers is not None:
	    self.transfers.GetUserStatus(msg)
	if self.privatechat is not None:
	    self.privatechat.GetUserStatus(msg)
	if self.userinfo is not None:
	    self.userinfo.GetUserStatus(msg)
	if self.userbrowse is not None:
	    self.userbrowse.GetUserStatus(msg)
	if self.chatrooms is not None:
            self.chatrooms.roomsctrl.GetUserStatus(msg)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))


    def GetUserStats(self,msg):
	if msg.user == self.config.sections["server"]["login"]:
	    self.speed = msg.avgspeed

        self.frame.GetUserStats(msg)
        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.GetUserStats(msg)
	if self.userinfo is not None:
	    self.userinfo.GetUserStats(msg)
	if self.userlist is not None:
	    self.userlist.GetUserStats(msg)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))

    def UserLeftRoom(self,msg):
        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.UserLeftRoom(msg)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))


    def QueuedDownloads(self,msg): 
#	if self.chatrooms is not None:
#	    self.chatrooms.roomsctrl.QueuedDownloads(msg) 
#	else: 
	    self.logMessage("%s %s" %(msg.__class__, vars(msg)))

    def GetPeerAddress(self,msg):
	for i in self.peerconns:
	    if i.username == msg.user and i.addr is None:
		if msg.port != 0 or i.tryaddr == 10:
		    if i.tryaddr == 10:
			self.logMessage(_("Server reported port 0 for the 10th time for user %s, giving up") %(msg.user),1)
		    elif i.tryaddr is not None:
			self.logMessage(_("Server reported non-zero port for user %s after %i retries") %(msg.user, i.tryaddr),1)
		    i.addr = (msg.ip, msg.port)
		    i.tryaddr = None
		    self.queue.put(slskmessages.OutConn(None, i.addr))
		    for j in i.msgs:
		        if j.__class__ is slskmessages.TransferRequest and self.transfers is not None:
                            self.transfers.gotAddress(j.req)
		else:
		    if i.tryaddr is None:
			i.tryaddr = 1
			self.logMessage(_("Server reported port 0 for user %s, retrying") %(msg.user),1)
		    else:
			i.tryaddr +=1
		    self.queue.put(slskmessages.GetPeerAddress(msg.user))
		break
	else:
	    import socket
	    if self.geoip:
	        cc = self.geoip.country_name_by_addr(msg.ip)
	    else:
	        cc = ""
	    if cc:
	        cc = " (%s)" % cc
	    else:
	        cc = ""
	    try:
		hostname = socket.gethostbyaddr(msg.ip)[0]
		message = _("IP address of %s is %s, name %s, port %i%s") %(msg.user,msg.ip,hostname,msg.port,cc)
	    except:
		message = _("IP address of %s is %s, port %i%s") %(msg.user,msg.ip,msg.port,cc)
	    self.logMessage(message)
	if self.users.has_key(msg.user):
	    self.users[msg.user].addr = (msg.ip,msg.port)

    def Relogged(self, msg):
	self.logMessage(_("Someone else is logging in with the same nickname, server is going to disconnect us"))
	self.frame.manualdisconnect = 1

    def OutConn(self, msg):
	for i in self.peerconns:
	    if i.addr == msg.addr and i.conn is None:
		if i.token is None:
		    i.init.conn = msg.conn
		    self.queue.put(i.init)
		else:
		    self.queue.put(slskmessages.PierceFireWall(msg.conn, i.token))
		i.conn = msg.conn
		for j in i.msgs:
		    if j.__class__ is slskmessages.UserInfoRequest and self.userinfo is not None:
			self.userinfo.InitWindow(i.username,msg.conn)
		    if j.__class__ is slskmessages.GetSharedFileList and self.userbrowse is not None:
			self.userbrowse.InitWindow(i.username,msg.conn)
		    if j.__class__ is slskmessages.FileRequest and self.transfers is not None:
			self.transfers.gotFileConnect(j.req,msg.conn)
		    if j.__class__ is slskmessages.TransferRequest and self.transfers is not None:
			self.transfers.gotConnect(j.req,msg.conn)
		    j.conn = msg.conn
		    self.queue.put(j)
		i.msgs = []
		break
		
	self.logMessage("%s %s" %(msg.__class__, vars(msg)),1)

    def IncConn(self,msg):
	self.logMessage("%s %s" %(msg.__class__, vars(msg)),1)

    def ConnectToPeer(self, msg):
	init = slskmessages.PeerInit(None,msg.user,msg.type,0)
        self.queue.put(slskmessages.OutConn(None,(msg.ip,msg.port),init))
        self.peerconns.append(PeerConnection(addr = (msg.ip,msg.port), username = msg.user, msgs = [], token = msg.token, init = init))

        self.logMessage("%s %s" %(msg.__class__, vars(msg)),1)

    def CheckUser(self, user, geoip, addr):
        if user in self.config.sections["server"]["banlist"]:
	        if self.config.sections["transfers"]["usecustomban"]:
	            return 0, _("Banned (%s)") % self.config.sections["transfers"]["customban"]
	        else:
	            return 0, _("Banned")
	if user in [i[0] for i in self.config.sections["server"]["userlist"]] and self.config.sections["transfers"]["enablebuddyshares"]:
	    # For sending buddy-only shares
	    return 2, ""
    	if user in [i[0] for i in self.config.sections["server"]["userlist"]]:
	    return 1, ""
    	if self.config.sections["transfers"]["friendsonly"]:
    	    return 0, _("Sorry, friends only")
    	if not geoip or not self.config.sections["transfers"]["geoblock"]:
    	    return 1, _("geoip")
    	cc = geoip.country_code_by_addr(addr)
    	if not cc:
    	    if self.config.sections["transfers"]["geopanic"]:
    	        return 0, _("Sorry, geographical paranoia")
    	    else:
    	        return 1, ""
    	if self.config.sections["transfers"]["geoblockcc"][0].find(cc) >= 0:
    	    return 0, _("Sorry, your country is blocked")
    	return 1, ""

    def GetSharedFileList(self,msg):
        self.logMessage("%s %s" %(msg.__class__, vars(msg)),1)
        for i in self.peerconns:
            if i.conn is msg.conn.conn:
	        user = i.username
		ip, port = i.addr
		break
	
	if user == self.config.sections["server"]["login"]:
		self.logMessage(_("%s is making a BrowseShares request, blocking possible spoofing attempt from IP %s port %s") %(user, ip, port), None)
		return
	self.logMessage(_("%s is making a BrowseShares request") %(user), None)
        addr = msg.conn.addr[0]
	checkuser, reason = self.CheckUser(user, self.geoip, addr)

	if checkuser == 1:
		self.queue.put(slskmessages.SharedFileList(msg.conn.conn,self.config.sections["transfers"]["sharedfilesstreams"]))
	elif checkuser == 2:
	    self.queue.put(slskmessages.SharedFileList(msg.conn.conn,self.config.sections["transfers"]["bsharedfilesstreams"]))
	else:
	    self.queue.put(slskmessages.SharedFileList(msg.conn.conn,{}))
	    

    def UserInfoReply(self,msg):
	for i in self.peerconns:
	    if i.conn is msg.conn.conn and self.userinfo is not None:
		# probably impossible to do this
		if i.username != self.config.sections["server"]["login"]:
			self.userinfo.ShowInfo(i.username, msg)
			
	
    def UserInfoRequest(self, msg):
	for i in self.peerconns:
	    if i.conn is msg.conn.conn:
	        user = i.username
		ip, port = i.addr
		break
	if user == self.config.sections["server"]["login"]:
		self.logMessage(_("Blocking %s from making a UserInfo request, possible spoofing attempt from IP %s port %s") %(user, ip, port), None)
		return
	if user in self.config.sections["server"]["banlist"]:
		self.logMessage(_("%s is banned, but is making a UserInfo request") %(user), 1)
		self.logMessage("%s %s" %(msg.__class__, vars(msg)),1)
		return
	try:
	    if sys.platform == "win32":
		    userpic = u"%s" % self.config.sections["userinfo"]["pic"]
		    if not os.path.exists(userpic):
		    	userpic = self.config.sections["userinfo"]["pic"]
	    else:
		    userpic = self.config.sections["userinfo"]["pic"]
	    f=open(userpic,'rb')
	    pic = f.read()
	    f.close()
	except:
	    pic = None
	descr = self.encode(eval(self.config.sections["userinfo"]["descr"], {}))
	
	if self.transfers is not None:
	    totalupl = self.transfers.getTotalUploadsAllowed()
	    queuesize = self.transfers.getUploadQueueSizes()[0]
	    slotsavail = not self.transfers.bandwidthLimitReached()
	    self.queue.put(slskmessages.UserInfoReply(msg.conn.conn,descr,pic,totalupl, queuesize,slotsavail))

	self.logMessage(_("%s is making a UserInfo request") %(user), None)
	self.logMessage("%s %s" %(msg.__class__, vars(msg)),1)
	


    def SharedFileList(self, msg):
	for i in self.peerconns:
	    if i.conn is msg.conn.conn and self.userbrowse is not None:
		if i.username != self.config.sections["server"]["login"]:
			self.userbrowse.ShowInfo(i.username, msg)

    def FileSearchResult(self, msg):
	for i in self.peerconns:
	    if i.conn is msg.conn.conn and self.search is not None:
	        if self.geoip:
	          if i.addr:
	            country = self.geoip.country_code_by_addr(i.addr[0])
	          else:
	            country = ""
	        else:
	          country = ""
		self.search.ShowResult(msg, i.username, country)

    def PierceFireWall(self, msg):
	for i in self.peerconns:
	    if i.token == msg.token and i.conn is None:
		if i.conntimer is not None:
		    i.conntimer.cancel()
		i.init.conn = msg.conn.conn
                self.queue.put(i.init)
                i.conn = msg.conn.conn
                for j in i.msgs:
                    if j.__class__ is slskmessages.UserInfoRequest and self.userinfo is not None:
                        self.userinfo.InitWindow(i.username,msg.conn.conn)
                    if j.__class__ is slskmessages.GetSharedFileList and self.userbrowse is not None:
                        self.userbrowse.InitWindow(i.username,msg.conn.conn)
		    if j.__class__ is slskmessages.FileRequest and self.transfers is not None:
			self.transfers.gotFileConnect(j.req,msg.conn.conn)
		    if j.__class__ is slskmessages.TransferRequest and self.transfers is not None:
			self.transfers.gotConnect(j.req,msg.conn.conn)
                    j.conn = msg.conn.conn
                    self.queue.put(j)
                i.msgs = []
		break

        self.logMessage("%s %s" %(msg.__class__, vars(msg)),1)

    def CantConnectToPeer(self, msg):
	for i in self.peerconns[:]:
	    if i.token == msg.token:
		if i.conntimer is not None:
		    i.conntimer.cancel()
		if i == self.GetDistribConn():
		    self.DistribConnClosed(i)
		self.peerconns.remove(i)
	        self.logMessage(_("Can't connect to %s (either way), giving up") % (i.username),1)
                for j in i.msgs: 
                    if j.__class__ in [slskmessages.TransferRequest,slskmessages.FileRequest] and self.transfers is not None:
                        self.transfers.gotCantConnect(j.req)

    def ConnectToPeerTimeout(self,msg):
	for i in self.peerconns[:]:
            if i == msg.conn:
		if i == self.GetDistribConn():
		    self.DistribConnClosed(i)
                self.peerconns.remove(i)
                self.logMessage(_("User %s does not respond to connect request, giving up") % (i.username),1)
                for j in i.msgs:
                    if j.__class__ in [slskmessages.TransferRequest,slskmessages.FileRequest] and self.transfers is not None:
                        self.transfers.gotCantConnect(j.req)

    def TransferTimeout(self, msg):
        if self.transfers is not None:
            self.transfers.TransferTimeout(msg)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))


    def FileDownload(self,msg):
        if self.transfers is not None:
            self.transfers.FileDownload(msg)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))

    def FileUpload(self,msg):
        if self.transfers is not None:
            self.transfers.FileUpload(msg)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))


    def FileRequest(self,msg):
        if self.transfers is not None:
            self.transfers.FileRequest(msg)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))

    def FileError(self,msg):
        if self.transfers is not None:
            self.transfers.FileError(msg)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))

    def TransferRequest(self,msg):
        if self.transfers is not None:
            self.transfers.TransferRequest(msg)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))

    def TransferResponse(self,msg):
        if self.transfers is not None:
            self.transfers.TransferResponse(msg)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))


    def QueueUpload(self,msg):
        if self.transfers is not None:
            self.transfers.QueueUpload(msg)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))

    def QueueFailed(self,msg):
        if self.transfers is not None:
            self.transfers.QueueFailed(msg)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))

    def PlaceholdUpload(self,msg):
	self.logMessage("%s %s" %(msg.__class__, vars(msg)),1)

    def PlaceInQueueRequest(self, msg):
        if self.transfers is not None:
            self.transfers.PlaceInQueueRequest(msg)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))

    def UploadQueueNotification(self, msg):
      self.logMessage("%s %s" %(msg.__class__, vars(msg)),1)
      username = None
      for i in self.peerconns:
            if i.conn is msg.conn.conn:
		username = i.username
                break
      if username is None:
        return
      if username in [i[0] for i in self.config.sections["server"]["userlist"]] and self.config.sections["transfers"]["remotedownloads"] == 1:
            self.logMessage(_("Your buddy, %s, is attempting to upload file(s) to you.")%(username), None)
      else:
            self.queue.put(slskmessages.MessageUser(username, _("[Automatic Message] ")+_("You are not allowed to send me files.")) )
            self.logMessage(_("%s is not allowed to send you file(s), but is attempting to, anyway. Warning Sent.")%(username), None)
            


    def UploadFailed(self,msg):
        if self.transfers is not None:
            self.transfers.UploadFailed(msg)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))


    def PlaceInQueue(self,msg):
        if self.transfers is not None:
            self.transfers.PlaceInQueue(msg)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))

    def FolderContentsResponse(self,msg):
        if self.transfers is not None:
		
		for i in self.peerconns:
			if i.conn is msg.conn.conn:
        	        	username = i.username
		# Check for a large number of files
		many=0
		folder = ""
		files = []
		for i in msg.list.keys():
			for j in msg.list[i].keys():
				if os.path.commonprefix([i,j]) == j:
					numfiles = len(msg.list[i][j])
					if numfiles > 100:
						many=1
						files = msg.list[i][j]
						folder = j
						
						
		if many:
			self.frame.download_large_folder(username, folder, files, numfiles, msg)
		else:
			self.transfers.FolderContentsResponse(msg)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))

    def FolderContentsRequest(self,msg):
	username = None
	checkuser = None
	for i in self.peerconns:
            if i.conn is msg.conn.conn:
		username = i.username
		checkuser, reason = self.CheckUser(username, None, None)
		
			
		break
	if not checkuser:
		self.queue.put(slskmessages.MessageUser(i.username, _("[Automatic Message] ")+reason) )
		return
	else:
		self.queue.put(slskmessages.MessageUser(i.username, _("Please try browsing me if you get 'File not shared' errors. This is an automatic message, you don't have to reply to it.") ) )
		
	if checkuser == 1:
		shares = self.config.sections["transfers"]["sharedfiles"]
	elif checkuser == 2:
		shares = self.config.sections["transfers"]["bsharedfiles"]
	else:
		response = self.queue.put(slskmessages.TransferResponse(msg.conn.conn,0,reason = reason, req=0) )
		shares = {}
	
	if checkuser:
		if shares.has_key(msg.dir.replace("\\",os.sep)[:-1]):
			self.queue.put(slskmessages.FolderContentsResponse(msg.conn.conn, msg.dir, shares[msg.dir.replace("\\",os.sep)[:-1]]))
		elif shares.has_key(msg.dir.replace("\\",os.sep)):
			self.queue.put(slskmessages.FolderContentsResponse(msg.conn.conn, msg.dir, shares[msg.dir.replace("\\",os.sep)]))
		else:
			if checkuser == 2:
				shares = self.config.sections["transfers"]["sharedfiles"]
				if shares.has_key(msg.dir.replace("\\",os.sep)[:-1]):
					self.queue.put(slskmessages.FolderContentsResponse(msg.conn.conn, msg.dir, shares[msg.dir.replace("\\",os.sep)[:-1]]))
				elif shares.has_key(msg.dir.replace("\\",os.sep)):
					self.queue.put(slskmessages.FolderContentsResponse(msg.conn.conn, msg.dir, shares[msg.dir.replace("\\",os.sep)]))
				
			
        
	self.logMessage("%s %s" %(msg.__class__, vars(msg)),1)

    def RoomList(self,msg):
	if self.chatrooms is not None:
	     self.chatrooms.roomsctrl.SetRoomList(msg)
	     self.setStatus("")
	else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))

    def GlobalUserList(self,msg):
        if self.globallist is not None:
             self.globallist.setGlobalUsersList(msg)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))

    def PeerTransfer(self,msg):
	if self.userinfo is not None and msg.msg is slskmessages.UserInfoReply:
	    self.userinfo.UpdateGauge(msg)
	if self.userbrowse is not None and msg.msg is slskmessages.SharedFileList:
	    self.userbrowse.UpdateGauge(msg)

    def TunneledMessage(self, msg):
	if msg.code in self.protothread.peerclasses.keys():
	    peermsg = self.protothread.peerclasses[msg.code](None)

  	    peermsg.parseNetworkMessage(msg.msg)
	    peermsg.tunneleduser = msg.user
	    peermsg.tunneledreq = msg.req
	    peermsg.tunneledaddr = msg.addr
	    self.callback([peermsg])
	else:
	    self.logMessage(_("Unknown tunneled message: %s") %(vars(msg)))

    def ExactFileSearch(self,msg):
	self.logMessage("%s %s" %(msg.__class__, vars(msg)),1)
	
    def FileSearchRequest(self, msg):
	for i in self.peerconns:
	    if i.conn == msg.conn.conn:
	        user = i.username
		self.processSearchRequest(msg.searchterm, user, msg.searchid, 1)
		
	    
    def SearchRequest(self, msg):
	self.processSearchRequest(msg.searchterm, msg.user, msg.searchid, 0)

    def DistribSearch(self,msg):
	self.processSearchRequest(msg.searchterm, msg.user, msg.searchid, 0)

    def processSearchRequest(self, searchterm, user, searchid, direct = 0):
        if searchterm is None:
            return
#	self.searchfile.write(searchterm+"\n")
#	self.searchfile.flush()
	checkuser, reason = self.CheckUser(user, None, None)
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
        list = [wordindex[i][:] for i in terms if wordindex.has_key(i)]
	if len(list) != len(terms) or len(list) == 0:
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
	if len(results) > 0 and self.transfers is not None:
     	    queuesizes = self.transfers.getUploadQueueSizes()
            slotsavail = not self.transfers.bandwidthLimitReached()
	    if len(results) > 0:
		message = slskmessages.FileSearchResult(None, user, geoip, searchid,results,fileindex,slotsavail, self.speed, queuesizes, fifoqueue)
		self.ProcessRequestToPeer(user, message)
		if direct:
		    self.logMessage(_("User %s is directly searching for %s, returning %i results") %(user,self.decode(searchterm),len(results)),1)
		else:
		    self.logMessage(_("User %s is searching for %s, returning %i results") %(user,self.decode(searchterm),len(results)),1)

    def NetInfo(self, msg):
	self.distribcache.update(msg.list)
	if len(self.distribcache) > 0:
	    self.queue.put(slskmessages.HaveNoParent(0))
	    if not self.GetDistribConn():
		user = self.distribcache.keys()[0]
		addr = self.distribcache[user]
		self.ProcessRequestToPeer(user, slskmessages.DistribConn(),None,addr)
	self.logMessage("%s %s" %(msg.__class__, vars(msg)),1)

    def DistribAlive(self, msg):
	self.logMessage("%s %s" %(msg.__class__, vars(msg)),1)

    def GetDistribConn(self):
	for i in self.peerconns:
	    if i.init.type == 'D':
		return i
	return None

    def DistribConnClosed(self, conn):
        del self.distribcache[conn.username]
        if len(self.distribcache) > 0:
            user = self.distribcache.keys()[0]
            addr = self.distribcache[user]
            self.ProcessRequestToPeer(user, slskmessages.DistribConn(),None,addr)
        else:
            self.queue.put(slskmessages.HaveNoParent(1))

    def GlobalRecommendations(self, msg):
        self.frame.GlobalRecommendations(msg)
    
    def Recommendations(self, msg):
        self.frame.Recommendations(msg)
    
    def ItemRecommendations(self, msg):
	self.frame.ItemRecommendations(msg)
    
    def SimilarUsers(self, msg):
        self.frame.SimilarUsers(msg)
    
    def ItemSimilarUsers(self, msg):
        self.frame.ItemSimilarUsers(msg)

    def RoomTickerState(self, msg):
        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.TickerSet(msg)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))
    
    def RoomTickerAdd(self, msg):
        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.TickerAdd(msg)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))
    
    def RoomTickerRemove(self, msg):
        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.TickerRemove(msg)
        else:
            self.logMessage("%s %s" %(msg.__class__, vars(msg)))

    def logTransfer(self, message, toUI = 0):
        if self.config.sections["logging"]["transfers"]:
            fn = os.path.join(self.config.sections["logging"]["logsdir"], "transfers.log")
            try:
                f = open(fn, "a")
                f.write(time.strftime("%c"))
                f.write(" %s\n" % message)
                f.close()
            except IOError, error:
                self.logMessage(_("Couldn't write to transfer log: %s") % error)
        if toUI:
	        self.logMessage(message)
        
class UserAddr:
    def __init__(self, addr = None, behindfw = None, status = None):
	self.addr = addr
	self.behindfw = behindfw
	self.status = status
