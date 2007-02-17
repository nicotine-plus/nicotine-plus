# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
# Based on code from PySoulSeek, original copyright note:
# Copyright (c) 2001-2003 Alexander Kanavin. All rights reserved.

import struct
import types
import zlib
from utils import _
import os

""" This module contains message classes, that networking and UI thread
exchange. Basically there are three types of messages: internal messages,
server messages and p2p messages (between clients)."""

Id = 99

def newId():
	global Id
	Id = Id + 1
	return Id

class InternalMessage:
	pass

class ConnectToServer(InternalMessage):
	pass

class Conn(InternalMessage):
	def __init__(self,conn = None,addr = None, init = None):
		self.conn = conn
		self.addr = addr
		self.init = init

class OutConn(Conn):
	""" UI thread sends this to make networking thread establish a connection,
	when a connection is established, networking thread returns an object 
	of this type."""
	pass

class IncConn(Conn):
	""" Sent by networking thread to indicate an incoming connection."""
	pass

class ConnClose(Conn):
	""" Sent by networking thread to indicate a connection has been closed."""
	pass

class ServerConn(OutConn):
	""" A connection to the server has been established"""
	pass

class ConnectError(InternalMessage):
	""" Sent when a socket exception occurs. It's up to UI thread to 
	handle this."""
	def __init__(self, connobj = None, err = None):
		self.connobj = connobj
		self.err = err

class IncPort(InternalMessage):
	""" Send by networking thread to tell UI thread the port number client 
	listens on."""
	def __init__(self, port = None):
		self.port = port

class PeerTransfer(InternalMessage):
	""" Used to indicate progress of long transfers. """
	def __init__(self, conn = None, total = None, bytes = None, msg = None):
		self.conn = conn
		self.bytes = bytes
		self.total = total
		self.msg = msg

class DownloadFile(InternalMessage):
	""" Sent by networking thread to indicate file transfer progress.
	Sent by UI to pass the file object to write and offset to resume download 
	from. """
	def __init__(self, conn = None, offset = None, file = None, filesize = None):
		self.conn = conn
		self.offset = offset
		self.file = file
		self.filesize = filesize

class UploadFile(InternalMessage):
	def __init__(self, conn = None, file = None, size = None, sentbytes = 0, offset = None):
		self.conn = conn
		self.file = file
		self.size = size
		self.sentbytes = sentbytes
		self.offset = offset

class FileError(InternalMessage):
	""" Sent by networking thread to indicate that a file error occured during
	filetransfer. """
	def __init__(self, conn = None, file = None, strerror = None):
		self.conn = conn
		self.file = file
		self.strerror = strerror

class SetUploadLimit(InternalMessage):
	""" Sent by the GUI thread to indicate changes in bandwidth shaping rules"""
	def __init__(self,uselimit,limit,limitby):
		self.uselimit = uselimit
		self.limit = limit
		self.limitby = limitby

class SetGeoBlock(InternalMessage):
	""" Sent by the GUI thread to indicate changes in GeoIP blocking"""
	def __init__(self,config):
		self.config = config

class RescanShares(InternalMessage):
	""" Sent by the GUI thread to itself to indicate the need to rescan shares in the background"""
	def __init__(self, shared,yieldfunction):
		self.shared = shared
		self.yieldfunction = yieldfunction
	
class RescanBuddyShares(InternalMessage):
	""" Sent by the GUI thread to itself to indicate the need to rescan shares in the background"""
	def __init__(self, shared,yieldfunction):
		self.shared = shared
		self.yieldfunction = yieldfunction

class DistribConn(InternalMessage):
	def __init__(self):
		pass

class Notify(InternalMessage):
	def __init__(self, msg):
		self.msg = msg

class SlskMessage:
	""" This is a parent class for all protocol messages. """
	
	def getObject(self,message,type, start=0, getintasshort=0, getsignedint=0):
		""" Returns object of specified type, extracted from message (which is
		a binary array). start is an offset."""
		intsize = struct.calcsize("<I")
		try:
			if type is types.IntType:
				if getintasshort:
					return intsize+start,struct.unpack("<H",message[start:start+struct.calcsize("<H")])[0]
				elif getsignedint:
					return intsize+start,struct.unpack("<i",message[start:start+intsize])[0]
				else:
					return intsize+start,struct.unpack("<I",message[start:start+intsize])[0]
			elif type is types.LongType:
				return struct.calcsize("<L")+start,struct.unpack("<L",message[start:start+struct.calcsize("<L")])[0]
			elif type is types.StringType:
				length = struct.unpack("<I",message[start:start+intsize])[0]
				string = message[start+intsize:start+length+intsize]
				return length+intsize+start, string
			else:
				return start,None
		except struct.error,error:
			print error
			return start,None

	def packObject(self,object):
		""" Returns object (integer, long or string packed into a 
		binary array."""
		if type(object) is types.IntType:
			return struct.pack("<i",object)
		elif type(object) is types.LongType:
			return struct.pack("<L", object)
		elif type(object) is types.StringType:
			return struct.pack("<i",len(object))+object
		elif type(object) is types.UnicodeType:
			print _("Warning: networking thread has to convert unicode string %s message %s") % (object, self.__class__)
			encoded = object.encode("utf-8",'replace')
			return struct.pack("<i",len(encoded))+encoded
		print _("Warning: unknown object type %s") % type(object)
		return ""
        
	def makeNetworkMessage(self):
		""" Returns binary array, that can be sent over the network"""
		print _("Empty message made, class %s") % self.__class__
		return None
    
	def parseNetworkMessage(self, message):
		""" Extracts information from the message and sets up fields 
		in an object"""
		print _("Can't parse incoming messages, class %s") % self.__class__
	
	def strrev(self, str):
		strlist = list(str)
		strlist.reverse()
		return ''.join(strlist)

class ServerMessage(SlskMessage):
	pass

class PeerMessage(SlskMessage):
	pass

class DistribMessage(SlskMessage):
	pass

class Login(ServerMessage):
	""" We sent this to the server right after the connection has been 
	established. Server responds with the greeting message. """
	
	def __init__(self, username=None, passwd=None, version = None):
		self.username = username
		self.passwd = passwd
		self.version = version
		
	def makeNetworkMessage(self):
		import md5
		m = md5.new()
		m.update(self.username+self.passwd)
		md5hash = m.hexdigest()
		message = self.packObject(self.username)+ self.packObject(self.passwd) + self.packObject(self.version) + self.packObject(md5hash) + self.packObject(1)
		return message


	def parseNetworkMessage(self,message):
		len1, self.success = 1, ord(message[0])
		if not self.success:
			len1,self.reason = self.getObject(message,types.StringType,len1)
		else:
			len1,self.banner = self.getObject(message,types.StringType,len1)
		try:
			len1,self.num = self.getObject(message, types.IntType,len1)
			# Unknown number
		#print self.num
		except Exception, error:
			print "Unpack number", error
		try:
			if len(message[len1:]) > 0:
				len1, self.checksum = self.getObject(message,types.StringType,len1)
			#print self.checksum
		except Exception, error:
			# Not an official client on the official server
			pass


class SetWaitPort(ServerMessage):
	""" Send this to server to indicate port number that we listen on."""
	def __init__(self, port=None):
		self.port = port
	
	def makeNetworkMessage(self):
		return self.packObject(self.port)

class GetPeerAddress(ServerMessage):
	""" Used to find out a peer's (ip,port) address."""
	def __init__(self, user = None):
		self.user = user
	
	def makeNetworkMessage(self):
		return self.packObject(self.user)
	
	def parseNetworkMessage(self,message):
		len,self.user = self.getObject(message,types.StringType)
		import socket
		len, self.ip = len+4, socket.inet_ntoa(self.strrev(message[len:len+4]))
		len,self.port = self.getObject(message, types.IntType,len, 1)
		
class AddUser(ServerMessage):
	""" Used to be kept updated about a user's status."""
	def __init__(self, user = None):
		self.user = user
	
	def makeNetworkMessage(self):
		return self.packObject(self.user)
	
	def parseNetworkMessage(self,message):
		len,self.user = self.getObject(message,types.StringType)
		len,self.userexists = len+1,ord(message[len])

class RemoveUser(ServerMessage):
	""" Used when we no longer want to be kept updated about a user's status."""
	def __init__(self, user = None):
		self.user = user
	
	def makeNetworkMessage(self):
		return self.packObject(self.user)

class GetUserStatus(ServerMessage):
	""" Server tells us if a user has gone away or has returned"""
	def __init__(self, user = None):
		self.user = user
		self.privileged = None

	def makeNetworkMessage(self):
		return self.packObject(self.user)

	def parseNetworkMessage(self,message):
	
		len,self.user = self.getObject(message,types.StringType)
		len,self.status = self.getObject(message, types.IntType,len)
		# Exception handler is for Soulfind compatibility
		try:
			len, self.privileged = len+1, ord(message[len])
		except:
			pass

class SetStatus(ServerMessage):
	""" We send our new status to the server """
	def __init__(self, status = None):
		self.status = status
	
	def makeNetworkMessage(self):
		return self.packObject(self.status)

class NotifyPrivileges(ServerMessage):
	""" Server tells us something about privileges"""
	def __init__(self, token = None, user = None):
		self.token = token
		self.user = user
		
	def parseNetworkMessage(self,message):
		len, self.token = self.getObject(message,types.IntType)
		len, self.user = self.getObject(message,types.StringType,len)
			
class AckNotifyPrivileges(ServerMessage):
	def __init__(self, token = None):
		self.token = token
		
	def makeNetworkMessage(self):
		return self.packObject(self.token)

class SayChatroom(ServerMessage):
	""" Either we want to say something in the chatroom, or someone did."""
	def __init__(self,room = None, msg = None):
		self.room = room
		self.msg = msg
	
	def makeNetworkMessage(self):
		return self.packObject(self.room)+self.packObject(self.msg)
	
	def parseNetworkMessage(self,message):
		len,self.room = self.getObject(message,types.StringType)
		len,self.user = self.getObject(message,types.StringType,len)
		len,self.msg = self.getObject(message,types.StringType,len)

class UserData:
	""" When we join a room the server send us a bunch of these, 
	for each user."""
	def __init__(self,list):
		self.status = list[0]
		self.avgspeed = list[1]
		self.downloadnum = list[2]
		self.something = list[3]
		self.files = list[4]
		self.dirs = list[5]
		self.slotsfull = list[6]

class JoinRoom(ServerMessage):
	""" Server sends us this message when we join a room. Contains users list
	with data on everyone."""
	def __init__(self,room = None):
		self.room = room
	
	def makeNetworkMessage(self):
		return self.packObject(self.room)
	
	def parseNetworkMessage(self,message):
		len,self.room = self.getObject(message,types.StringType)
		self.users = self.getUsers(message[len:])
	
	def getUsers(self,message):
		len,numusers = self.getObject(message,types.IntType)
		users = []
		for i in range(numusers):
			len,username = self.getObject(message,types.StringType,len)
			users.append([username,None,None,None,None,None,None,None])
		len, statuslen = self.getObject(message,types.IntType,len)
		for i in range(statuslen):
			len, users[i][1] = self.getObject(message,types.IntType,len)
	#	len, something = self.getObject(message, types.StringType, len)
		len, statslen = self.getObject(message,types.IntType,len)
		for i in range(statslen):
			len, users[i][2] = self.getObject(message,types.IntType,len,getsignedint=1)
		#            len, users[i][2] = self.getObject(message,types.IntType,len)
			len, users[i][3] = self.getObject(message,types.IntType,len)
			len, users[i][4] = self.getObject(message,types.IntType,len)
			len, users[i][5] = self.getObject(message,types.IntType,len)
			len, users[i][6] = self.getObject(message,types.IntType,len)
	#        len, something = self.getObject(message, types.StringType, len)
		len, slotslen = self.getObject(message,types.IntType,len)
		for i in range(slotslen):
			len, users[i][7] = self.getObject(message,types.IntType,len)
		usersdict={}
		for i in users:
			usersdict[i[0]] = UserData(i[1:])
		return usersdict

class LeaveRoom(ServerMessage):
	""" We send this when we want to leave a room."""
	def __init__(self,room = None):
		self.room = room
	
	def makeNetworkMessage(self):
		return self.packObject(self.room)
	
	def parseNetworkMessage(self,message):
		self.room = self.getObject(message,types.StringType)[1]


class UserJoinedRoom(ServerMessage):
	""" Server tells us someone has just joined the room."""
	def parseNetworkMessage(self,message):
		len,self.room = self.getObject(message,types.StringType)
		len,self.username = self.getObject(message,types.StringType,len)
		i = [None,None,None,None,None,None,None]
		len, i[0] = self.getObject(message,types.IntType,len)
		len, i[1] = self.getObject(message,types.IntType,len,getsignedint=1)
		for j in range(2,7):
			len, i[j] =(self.getObject(message,types.IntType,len))
		self.userdata = UserData(i)

class UserLeftRoom(ServerMessage):
	""" Well, the opposite."""
	def parseNetworkMessage(self,message):
		len,self.room = self.getObject(message,types.StringType)
		len,self.username = self.getObject(message,types.StringType,len)

class RoomTickerState(ServerMessage):
	def __init__(self):
		self.room = None
		self.user = None
		self.msgs = {}
	
	def parseNetworkMessage(self,message):
		len,self.room = self.getObject(message,types.StringType)
		len,n = self.getObject(message,types.IntType,len)
		for i in range(n):
			len,user = self.getObject(message,types.StringType, len)
			len,msg = self.getObject(message,types.StringType, len)
			self.msgs[user] = msg

class RoomTickerAdd(ServerMessage):
	def __init__(self):
		self.room = None
		self.user = None
		self.msg = None
	
	def parseNetworkMessage(self,message):
		len,self.room = self.getObject(message,types.StringType)
		len,self.user = self.getObject(message,types.StringType,len)
		len,self.msg = self.getObject(message,types.StringType,len)

class RoomTickerRemove(ServerMessage):
	def __init__(self, room = None):
		self.user = None
		self.room = room
	
	def parseNetworkMessage(self,message):
		len,self.room = self.getObject(message,types.StringType)
		len,self.user = self.getObject(message,types.StringType, len)

class RoomTickerSet(ServerMessage):
	def __init__(self, room = None, msg = None):
		self.room = room
		if not msg:
			self.msg = ""
		else:
			self.msg = msg

	def makeNetworkMessage(self):
		return self.packObject(self.room) + self.packObject(self.msg)

class ConnectToPeer(ServerMessage):
	""" Either we ask server to tell someone else we want to establish a 
	connection with him or server tells us someone wants to connect with us.
	Used when the side that wants a connection can't establish it, and tries
	to go the other way around.
	"""
	def __init__(self, token = None, user = None, type = None):
		self.token = token
		self.user = user
		self.type = type
	
	def makeNetworkMessage(self):
		return self.packObject(self.token)+self.packObject(self.user)+self.packObject(self.type)
	
	def parseNetworkMessage(self,message):
		len,self.user = self.getObject(message,types.StringType)
		len,self.type = self.getObject(message,types.StringType,len)
		import socket
		len, self.ip = len+4, socket.inet_ntoa(self.strrev(message[len:len+4]))
		len,self.port = self.getObject(message, types.IntType, len, 1)
		len,self.token = self.getObject(message, types.IntType, len)
	
class MessageUser(ServerMessage):
	""" Chat phrase sent to someone or received by us in private"""
	def __init__(self, user = None, msg = None):
		self.user = user
		self.msg = msg
	
	def makeNetworkMessage(self):
		return self.packObject(self.user)+self.packObject(self.msg)
	
	def parseNetworkMessage(self,message):
		len,self.msgid = self.getObject(message,types.IntType)
		len,self.timestamp = self.getObject(message,types.IntType, len)
		len,self.user = self.getObject(message,types.StringType, len)
		len,self.msg = self.getObject(message,types.StringType, len)

class MessageAcked(ServerMessage):
	""" Confirmation of private chat message.
	If we don't send it, the server will keep sending the chat phrase to us.
	"""
	def __init__(self, msgid = None):
		self.msgid = msgid
	
	def makeNetworkMessage(self):
		return self.packObject(self.msgid)

class FileSearch(ServerMessage):
	""" We send this to the server when we search for something."""
	""" Server send this to tell us someone is searching for something."""
	def __init__(self, requestid = None, text = None):
		self.searchid = requestid
		self.searchterm = text
	
	def makeNetworkMessage(self):
		return self.packObject(self.searchid)+self.packObject(self.searchterm)
	
	def parseNetworkMessage(self,message):
		len, self.user = self.getObject(message,types.StringType)
		len, self.searchid = self.getObject(message,types.IntType, len)
		len, self.searchterm = self.getObject(message,types.StringType, len)

class WishlistSearch(FileSearch):
	pass

class QueuedDownloads(ServerMessage):
	""" Server sends this to indicate if someone has download slots available 
	or not. """
	def parseNetworkMessage(self, message):
		len, self.user = self.getObject(message,types.StringType)
		len, self.slotsfull = self.getObject(message,types.IntType, len)

class SendSpeed(ServerMessage):
	""" We used to send this after a finished download to let the server update
	the speed statistics for a user"""
	def __init__(self, user = None, speed = None):
		self.user = user
		self.speed = speed
	
	def makeNetworkMessage(self):
		return self.packObject(self.user)+self.packObject(self.speed)

class SendUploadSpeed(ServerMessage):
	""" We now send this after a finished upload to let the server update
	the spped statistics for a user"""
	def __init__(self, speed = None):
		self.speed = speed
	
	def makeNetworkMessage(self):
		return self.packObject(self.speed)
    
class SharedFoldersFiles(ServerMessage):
	""" We send this to server to indicate the number of folder and files
	that we share """
	def __init__(self, folders = None, files = None):
		self.folders = folders
		self.files = files
	
	def makeNetworkMessage(self):
		return self.packObject(self.folders)+self.packObject(self.files)

class GetUserStats(ServerMessage):
	""" Server sends this to indicate change in user's statistics"""
	def __init__(self, user = None):
		self.user = user
	
	def makeNetworkMessage(self):
		return self.packObject(self.user)
	
	def parseNetworkMessage(self, message):
		len, self.user = self.getObject(message,types.StringType)
		len, self.avgspeed = self.getObject(message,types.IntType, len, getsignedint = 1)
		len, self.downloadnum = self.getObject(message,types.IntType, len)
		len, self.something = self.getObject(message,types.IntType, len)
		len, self.files = self.getObject(message,types.IntType, len)
		len, self.dirs = self.getObject(message,types.IntType, len)

class Relogged(ServerMessage):
	""" Server sends this if someone else logged in under our nickname
	and then disconnects us """
	def parseNetworkMessage(self, message):
		pass

class PlaceInLineResponse(ServerMessage):
	""" Server sends this to indicate change in place in queue while we're
	waiting for files from other peer """
	def __init__(self, user = None, req = None, place = None):
		self.req = req
		self.user = user
		self.place = place
	
	def makeNetworkMessage(self):
		return self.packObject(self.user)+self.packObject(self.req)+self.packObject(self.place)
	
	def parseNetworkMessage(self, message):
		len, self.user = self.getObject(message,types.StringType)
		len, self.req = self.getObject(message,types.IntType, len)
		len, self.place = self.getObject(message,types.IntType, len)

class RoomAdded(ServerMessage):
	""" Server tells us a new room has been added"""
	def parseNetworkMessage(self, message):
		self.room = self.getObject(message,types.StringType)[1]

class RoomRemoved(ServerMessage):
	""" Server tells us a room has been removed"""
	def parseNetworkMessage(self, message):
		self.room = self.getObject(message,types.StringType)[1]

class RoomList(ServerMessage):
	""" Server tells us a list of rooms"""
	def __init__(self):
		pass
	
	def makeNetworkMessage(self):
		return ""
	
	def parseNetworkMessage(self, message):
	
		len,numrooms = self.getObject(message,types.IntType)
		self.rooms = []
		for i in range(numrooms):
			len,room = self.getObject(message,types.StringType,len)
			self.rooms.append([room,None])
	
		len,numusercounts = self.getObject(message,types.IntType, len)
		for i in range(numusercounts):
			len,usercount = self.getObject(message,types.IntType,len)
			self.rooms[i][1] = usercount


class ExactFileSearch(ServerMessage):
	""" Someone is searching for a file with an exact name """
	def parseNetworkMessage(self, message):
		len,self.user = self.getObject(message,types.StringType)
		len,self.req = self.getObject(message,types.IntType,len)
		len,self.file = self.getObject(message,types.StringType,len)
		len,self.folder = self.getObject(message,types.StringType,len)
		len,self.size = self.getObject(message,types.IntType,len)
		len,self.size2 = self.getObject(message,types.IntType,len)
		len,self.checksum = self.getObject(message,types.IntType,len)

class AdminMessage(ServerMessage):
	""" A global message from the admin has arrived """
	def parseNetworkMessage(self, message):
		self.msg = self.getObject(message,types.StringType)[1]

class GlobalUserList(JoinRoom):
	""" We send this to get a global list of all users online """
	def __init__(self):
		pass
	
	def makeNetworkMessage(self):
		return ""
	
	def parseNetworkMessage(self, message):
		self.users = self.getUsers(message)


class TunneledMessage(ServerMessage):
	def __init__(self, user = None, req = None, code = None, msg = None):
		self.user = user
		self.req = req
		self.code = code
		self.msg = msg
	
	def makeNetworkMessage(self,message):
		return self.packObject(self.user)+self.packObject(self.req)+self.packObject(self.code)+self.packObject(self.msg)

	def parseNetworkMessage(self,message):
		len,self.user = self.getObject(message,types.StringType)
		len,self.code = self.getObject(message,types.IntType,len)
		len,self.req = self.getObject(message,types.IntType,len)
		len,ip = len+4, socket.inet_ntoa(self.strrev(message[len:len+4]))
		len,port = self.getObject(message, types.IntType,len,1)
		self.addr = (ip,port)
		len,self.msg = self.getObject(message,types.StringType,len)

class Msg83(ServerMessage):
	def __init__(self):
		pass
	
	def parseNetworkMessage(self, message):
		len, self.num = self.getObject(message,types.IntType)

class Msg84(Msg83):
	pass

class Msg85(Msg83):
	pass


class ParentInactivityTimeout(Msg83):
	pass

class SearchInactivityTimeout(Msg83):
	pass

class MinParentsInCache(Msg83):
	pass
class Msg12547(Msg83):
	pass

class UploadQueueNotification(PeerMessage):
	def __init__(self,conn):
		self.conn = conn
	
	def makeNetworkMessage(self):
		return ""
	
	def parseNetworkMessage(self, message):
		return ""

    
class Msg89(Msg83):
	pass

class DistribAliveInterval(Msg83):
	pass

class WishlistInterval(Msg83):
	pass

class PrivilegedUsers(ServerMessage):
	""" A list of thise who made a donation """
	def __init__(self):
		pass
	
	def parseNetworkMessage(self, message):
		try:
			x = zlib.decompress(message)
			message =  x[4:]
		except Exception, error:
			pass
		self.users = []
		len, numusers = self.getObject(message,types.IntType)
		for i in range(numusers):
			len, user = self.getObject(message,types.StringType, len)
			self.users.append(user)

class CheckPrivileges(ServerMessage):
	def __init__(self):
		pass
	
	def makeNetworkMessage(self):
		return ""
	
	def parseNetworkMessage(self, message):
		len, self.days = self.getObject(message, types.IntType)

class AddToPrivileged(ServerMessage):
	def __init__(self):
		pass
	
	def parseNetworkMessage(self, message):
		l2, self.user = self.getObject(message, types.StringType)

class CantConnectToPeer(ServerMessage):
	""" We send this to say we can't connect to peer after it has asked us
	to connect. We receive this if we asked peer to connect and it can't do
	this. So this message means a connection can't be established either way.
	"""
	def __init__(self, token = None, user = None):
		self.token = token
		self.user = user
	
	def makeNetworkMessage(self):
		return self.packObject(self.token)+self.packObject(self.user)
	
	def parseNetworkMessage(self, message):
		len, self.token = self.getObject(message, types.IntType)

class CantCreateRoom(ServerMessage):
	""" Server tells us a new room cannot be created"""
	def parseNetworkMessage(self, message):
		self.room = self.getObject(message,types.StringType)[1]

class ServerPing(ServerMessage):
	def makeNetworkMessage(self):
		return ""
		
	def parseNetworkMessage(self, message):
		pass

class AddThingILike(ServerMessage):
	""" Add item to our likes list """
	def __init__(self, thing = None):
		self.thing = thing
	
	def makeNetworkMessage(self):
		return self.packObject(self.thing)

class AddThingIHate(AddThingILike):
	pass

class RemoveThingILike(ServerMessage):
	""" Remove item from our likes list """
	def __init__(self, thing = None):
		self.thing = thing
	
	def makeNetworkMessage(self):
		return self.packObject(self.thing)

class RemoveThingIHate(RemoveThingILike):
	pass

class GlobalRecommendations(ServerMessage):
	def __init__(self):
		self.recommendations = None
	
	def makeNetworkMessage(self):
		return ""
	
	def parseNetworkMessage(self, message):
		self.unpack_recommendations(message)
	
	def unpack_recommendations(self, message, len = 0):
		len, num = self.getObject(message, types.IntType, len)
		self.recommendations = {}
		for i in range(num):
			len, key = self.getObject(message, types.StringType, len)
			len, rating = self.getObject(message, types.IntType, len)
			self.recommendations[key] = rating

class Recommendations(GlobalRecommendations):
	pass
    
class ItemRecommendations(GlobalRecommendations):
	def __init__(self, thing = None):
		GlobalRecommendations.__init__(self)
		self.thing = thing
	
	def makeNetworkMessage(self):
		return self.packObject(self.thing)
	
	def parseNetworkMessage(self, message):
		len, self.thing = self.getObject(message, types.StringType)
		self.unpack_recommendations(message, len)

class SimilarUsers(ServerMessage):
	def __init__(self):
		self.users = None
	
	def makeNetworkMessage(self):
		return ""
	
	def parseNetworkMessage(self, message):
		self.users = {}
		len, num = self.getObject(message, types.IntType)
		for i in range(num):
			len, user = self.getObject(message, types.StringType, len)
			len, rating = self.getObject(message, types.IntType, len)
			self.users[user] = rating

class ItemSimilarUsers(ServerMessage):
	def __init__(self, thing = None):
		self.thing = thing
		self.users = None
	
	def makeNetworkMessage(self):
		return self.packObject(self.thing)
	
	def parseNetworkMessage(self, message):
		self.users = []
		len, self.thing = self.getObject(message, types.StringType)
		len, num = self.getObject(message, types.IntType, len)
		for i in range(num):
			len, user = self.getObject(message, types.StringType, len)
			self.users.append(user)

class RoomSearch(ServerMessage):
	def __init__(self, room=None, requestid = None, text = None):
		self.room = room
		self.searchid = requestid
		self.searchterm = text
	
	def makeNetworkMessage(self):
		return self.packObject(self.room)+self.packObject(self.searchid)+self.packObject(self.searchterm)
	
	def parseNetworkMessage(self,message):
		len, self.user = self.getObject(message,types.StringType)
		len, self.searchid = self.getObject(message,types.IntType, len)
		len, self.searchterm = self.getObject(message,types.StringType, len)

class UserSearch(ServerMessage):
	def __init__(self, user=None, requestid = None, text = None):
		self.suser = user
		self.searchid = requestid
		self.searchterm = text
	
	def makeNetworkMessage(self):
		return self.packObject(self.suser)+self.packObject(self.searchid)+self.packObject(self.searchterm)
	
	def parseNetworkMessage(self,message):
		len, self.user = self.getObject(message,types.StringType)
		len, self.searchid = self.getObject(message,types.IntType, len)
		len, self.searchterm = self.getObject(message,types.StringType, len)


class PierceFireWall(PeerMessage):
	""" This is the very first message send by peer that established a 
	connection, if it has been asked by other peer to do so. Token is taken
	from ConnectToPeer server message."""
	def __init__(self, conn, token = None):
		self.conn = conn
		self.token = token
	
	def makeNetworkMessage(self):
		return self.packObject(self.token)
		
	def parseNetworkMessage(self,message):
		len, self.token = self.getObject(message, types.IntType)

class PeerInit(PeerMessage):
	""" This message is sent by peer that initiated a connection, not
	necessarily a peer that actually established it. Token apparently
	can be anything. Type is 'P' if it's anything but filetransfer, 'F' 
	otherwise"""
	def __init__(self, conn, user = None, type = None, token = None):
		self.conn = conn
		self.user = user
		self.type = type
		self.token = token
	
	def makeNetworkMessage(self):
		return self.packObject(self.user)+self.packObject(self.type)+self.packObject(self.token)
	
	def parseNetworkMessage(self, message):
		len, self.user = self.getObject(message, types.StringType)
		len, self.type = self.getObject(message, types.StringType,len)
		len, self.token = self.getObject(message, types.IntType, len)

class UserInfoRequest(PeerMessage):
	""" Ask other peer to send user information, picture and all."""
	def __init__(self,conn):
		self.conn = conn
	
	def makeNetworkMessage(self):
		return ""
	
	def parseNetworkMessage(self,message):
		pass



class UserInfoReply(PeerMessage):
	""" Peer responds with this, when asked for user information."""
	def __init__(self,conn,descr = None, pic = None, totalupl = None, queuesize = None, slotsavail = None):
		self.conn = conn
		self.descr = descr
		self.pic = pic
		self.totalupl = totalupl
		self.queuesize = queuesize
		self.slotsavail = slotsavail
	
	def parseNetworkMessage(self,message):
		pos, self.descr = self.getObject(message, types.StringType)
		pos, self.has_pic = pos+1, message[pos]
		if ord(self.has_pic):
			pos, self.pic = self.getObject(message, types.StringType,pos)
		pos, self.totalupl = self.getObject(message, types.IntType, pos)
		pos, self.queuesize = self.getObject(message, types.IntType, pos)
		if len(message[pos:]) == 1:
			# Old Nicotine clients send bool instead int
			try:
				pos, self.slotsavail = pos+1, ord(message[pos])
			except Exception, e:
				self.slotsavail = 0
				
		else:
			pos, self.slotsavail = self.getObject(message, types.IntType, pos)



	def makeNetworkMessage(self):
		if self.pic is not None:
			pic = chr(1) + self.packObject(self.pic)
		else:
			pic = chr(0)
		return self.packObject(self.descr)+pic+self.packObject(self.totalupl)+self.packObject(self.queuesize)+self.packObject(self.slotsavail)


class SharedFileList(PeerMessage):
	""" Peer responds with this when asked for a filelist."""
	def __init__(self,conn, list = None):
		self.conn = conn
		self.list = list
	 
	def parseNetworkMessage(self, message, nozlib = 0):

		if not nozlib:
			try:
				message=zlib.decompress(message)
			except Exception, error:
				print error
				self.list={}
				return

		list={}
		len, ndir = self.getObject(message,types.IntType)
		for i in range(ndir):
			len, dir = self.getObject(message,types.StringType, len)
			len, nfiles = self.getObject(message,types.IntType, len)
			list[dir] = []
			for j in range(nfiles):
				len, code = len+1, ord(message[len])
				len, name = self.getObject(message,types.StringType, len)
				len, size1 = self.getObject(message,types.LongType, len)
				len, size2 = self.getObject(message,types.LongType, len)
				size = (size2 << 32) + size1
		
				len, ext = self.getObject(message,types.StringType, len)
				len, numattr = self.getObject(message, types.IntType, len)
				attrs = []
				for k in range(numattr):
					len, attrnum = self.getObject(message,types.IntType, len)
					len, attr = self.getObject(message,types.IntType, len)
					attrs.append(attr)
				list[dir].append([code,name,size,ext,attrs])
		self.list = list

	def makeNetworkMessage(self, nozlib = 0):
		msg = ""
		msg = msg + self.packObject(len(self.list.keys()))
		for i in self.list.keys():
			msg = msg + self.packObject(i.replace(os.sep,"\\")) + self.list[i]
		if not nozlib:
			return zlib.compress(msg)
		else:
			return msg

class GetSharedFileList(PeerMessage):
	""" Ask the peer for a filelist. """ 
	def __init__(self,conn):
	
		self.conn = conn
	
	def parseNetworkMessage(self,message):
		pass
	
	def makeNetworkMessage(self):
		return ""

class FileSearchRequest(PeerMessage):
	""" We send this to the peer when we search for something."""
	""" Peer sends this to tell us he is  searching for something."""
	def __init__(self, conn, requestid = None, text = None):
		self.conn = conn
		self.requestid = requestid
		self.text = text
	
	def makeNetworkMessage(self):
		return self.packObject(self.requestid)+self.packObject(self.text)
	
	def parseNetworkMessage(self,message):
		len, self.searchid = self.getObject(message,types.IntType)
		len, self.searchterm = self.getObject(message,types.StringType, len)


class FileSearchResult(PeerMessage):
	""" Peer sends this when it has a file search match."""
	def __init__(self,conn, user = None, geoip = None, token = None, list = None, fileindex = None, freeulslots = None, ulspeed = None, inqueue = None, fifoqueue = None):
		self.conn = conn
		self.user = user
		self.geoip = geoip
		self.token = token
		self.list = list
		self.fileindex = fileindex
		self.freeulslots = freeulslots
		self.ulspeed = ulspeed 
		self.inqueue = inqueue
		self.fifoqueue = fifoqueue
	
	def parseNetworkMessage(self, message):
		try:
			message = zlib.decompress(message)
		except Exception, error:
			print error
			self.list={}
			return
	
		len, self.user = self.getObject(message,types.StringType)
		len, self.token = self.getObject(message,types.IntType,len)
		len, nfiles = self.getObject(message,types.IntType, len)
		list = []
		for i in range(nfiles):
			len, code = len+1, ord(message[len])
			len, name = self.getObject(message,types.StringType, len)
			len, size1 = self.getObject(message,types.LongType, len)
			len, size2 = self.getObject(message,types.LongType, len)
			size = (size2 << 32) + size1
			len, ext = self.getObject(message,types.StringType, len)
			len, numattr = self.getObject(message, types.IntType, len)
			attrs = []
			if numattr:
				for j in range(numattr):
					len, attrnum = self.getObject(message,types.IntType, len)
					len, attr = self.getObject(message,types.IntType, len)
					attrs.append(attr)
			list.append([code,name,size,ext,attrs])
		self.list = list
		len, self.freeulslots = len+1, ord(message[len])
		len, self.ulspeed = self.getObject(message,types.IntType, len, getsignedint=1)
		len, self.inqueue = self.getObject(message,types.IntType, len)
        
	def makeNetworkMessage(self):
		filelist = []
		for i in self.list:
			try:
				filelist.append(self.fileindex[str(i)])
			except:
				pass
	
		if self.fifoqueue:
			queuesize = self.inqueue[0]
		else:
			count = 0
			for i in filelist:
				if i[0][-4:].lower() == ".ogg":
					count += 1
				else:
					count -= 1
			if count > 0:
				queuesize = self.inqueue[1]
			else:
				queuesize = self.inqueue[0]

		msg = self.packObject(self.user)+self.packObject(self.token)+self.packObject(len(filelist))
		for i in filelist:
			msg = msg+chr(1)+self.packObject(i[0].replace(os.sep,"\\"))+self.packObject(i[1])+self.packObject(0)
			if i[2] is None:
				# No metadata
				msg = msg + self.packObject('')+self.packObject(0)
			else:
				msg = msg + self.packObject("mp3") + self.packObject(3)
				msg = msg + self.packObject(0) + self.packObject(i[2][0])+self.packObject(1)+ self.packObject(i[3])+self.packObject(2)+self.packObject(i[2][1])
		msg = msg+chr(self.freeulslots)+self.packObject(self.ulspeed)+self.packObject(queuesize)
		return zlib.compress(msg)

class FolderContentsRequest(PeerMessage):
	""" Ask the peer to send us the contents of a single folder. """
	def __init__(self, conn, dir=None):
		self.conn = conn
		self.dir = dir
	
	def makeNetworkMessage(self):
		return self.packObject(1)+self.packObject(self.dir)
	
	def parseNetworkMessage(self, message):
		len, self.something = self.getObject(message, types.IntType)
		len, self.dir = self.getObject(message, types.StringType, len)

class FolderContentsResponse(PeerMessage):
	""" Peer tells us the contents of a particular folder (with all subfolders)
	""" 
	def __init__(self, conn, dir = None, list = None):
		self.conn = conn
		self.dir = dir
		self.list = list

	def parseNetworkMessage(self, message):
		try:
			message = zlib.decompress(message)
		except Exception, error:
			print error
			self.list={}
			return
	#        f = open("ttt","w")
	#        f.write(message)
	#        f.close()
		list={}
		len, nfolders = self.getObject(message,types.IntType)
		for h in range(nfolders):
			len, folder = self.getObject(message,types.StringType, len)
			list[folder]={}
			len, ndir = self.getObject(message,types.IntType, len)
		
			for i in range(ndir):
				len, dir = self.getObject(message,types.StringType, len)
				len, nfiles = self.getObject(message,types.IntType, len)
				list[folder][dir] = []
				for j in range(nfiles):
					len, code = len+1, ord(message[len])
					len, name = self.getObject(message,types.StringType, len)
					len, size1 = self.getObject(message,types.LongType, len)
					len, size2 = self.getObject(message,types.LongType, len)
					size = (size2 << 32) + size1
					len, ext = self.getObject(message,types.StringType, len)
					len, numattr = self.getObject(message, types.IntType, len)
					attrs = []
					for k in range(numattr):
						len, attrnum = self.getObject(message,types.IntType, len)
						len, attr = self.getObject(message,types.IntType, len)
						attrs.append(attr)
					list[folder][dir].append([code,name,size,ext,attrs])
		self.list = list

	def makeNetworkMessage(self):
		msg = self.packObject(1) + self.packObject(self.dir) + self.packObject(1) + self.packObject(self.dir) + self.packObject(len(self.list))
		for i in self.list:
	
			msg = msg+chr(1)+self.packObject(i[0])+self.packObject(i[1])+self.packObject(0)
			if i[2] is None:
				msg = msg + self.packObject('')+self.packObject(0)
			else:
				msg = msg + self.packObject("mp3") + self.packObject(3)
				msg = msg + self.packObject(0) + self.packObject(i[2][0])+self.packObject(1)+ self.packObject(i[3])+self.packObject(2)+self.packObject(i[2][1])
		return zlib.compress(msg)

class TransferRequest(PeerMessage):
	""" Request a file from peer, or tell a peer that we want to send a file to
	them. """
	def __init__(self,conn, direction = None, req = None, file = None, filesize = None):
		self.conn = conn
		self.direction = direction
		self.req = req
		self.file = file
		self.filesize = filesize
	
	def makeNetworkMessage(self):
		msg = self.packObject(self.direction)+self.packObject(self.req)+self.packObject(self.file)
		if self.filesize is not None and self.direction == 1:
			msg = msg+self.packObject(self.filesize) + self.packObject(0)
		return msg
	
	def parseNetworkMessage(self,message):
	
		len,self.direction = self.getObject(message,types.IntType)
		len,self.req = self.getObject(message,types.IntType,len)
		len,self.file = self.getObject(message,types.StringType,len)
		if self.direction == 1:
			len,self.filesize = self.getObject(message,types.IntType,len)

class TransferResponse(PeerMessage):
	""" Response to the TreansferRequest - either we (or other peer) agrees, or 
	tells the reason for rejecting filetransfer. """
	def __init__(self,conn, allowed = None, reason = None, req = None, filesize=None):
		self.conn = conn
		self.allowed = allowed
		self.req = req
		self.reason = reason
		self.filesize = filesize
	
	def makeNetworkMessage(self):
		msg = self.packObject(self.req) + chr(self.allowed)
		if self.reason is not None:
			msg = msg + self.packObject(self.reason)
		if self.filesize is not None:
			msg = msg + self.packObject(self.filesize) + self.packObject(0)
		return msg
	
	def parseNetworkMessage(self,message):
		len,self.req = self.getObject(message,types.IntType)
		len, self.allowed = len+1,ord(message[len])
		if message[len:] != "":
			if self.allowed:
				len,self.filesize = self.getObject(message,types.IntType,len)
			else:
				len,self.reason = self.getObject(message,types.StringType,len)


class PlaceholdUpload(PeerMessage):
	def __init__(self,conn, file = None):
		self.conn = conn
		self.file = file
	
	def makeNetworkMessage(self):
		return self.packObject(self.file)
	
	def parseNetworkMessage(self,message):
		len,self.file = self.getObject(message,types.StringType)

class QueueUpload(PlaceholdUpload):
	pass

class UploadFailed(PlaceholdUpload):
	pass

class PlaceInQueue(PeerMessage):
	def __init__(self,conn, filename = None, place = None):
		self.conn = conn
		self.filename = filename
		self.place = place
	
	def makeNetworkMessage(self):
		return self.packObject(self.filename) + self.packObject(self.place)
	
	def parseNetworkMessage(self,message):
		len,self.filename = self.getObject(message,types.StringType)
		len, self.place = self.getObject(message,types.IntType,len)

class PlaceInQueueRequest(PlaceholdUpload):
	pass

class QueueFailed(PeerMessage):
	def __init__(self,conn, file = None, reason = None):
		self.conn = conn
		self.file = file
		self.reason = reason
	
	def makeNetworkMessage(self):
		return self.packObject(self.file)+self.packObject(self.reason)
	
	def parseNetworkMessage(self,message):
		len,self.file = self.getObject(message,types.StringType)
		len,self.reason = self.getObject(message,types.StringType,len)


class FileRequest(PeerMessage):
	""" Request a file from peer, or tell a peer that we want to send a file to
	them. """
	def __init__(self,conn, req = None):
		self.conn = conn
		self.req = req
	
	def makeNetworkMessage(self):
		msg = self.packObject(self.req)
		return msg

class HaveNoParent(ServerMessage):
	def __init__(self, noparent = None):
		self.noparent = noparent
	
	def makeNetworkMessage(self):
		return chr(self.noparent)

class DistribAlive(DistribMessage):
	def __init__(self, conn):
		self.conn = conn
	
	def parseNetworkMessage(self, message):
		pass

class DistribSearch(DistribMessage):
	""" Search request that arrives through the distributed network """
	def __init__(self,conn):
		self.conn = conn
	
	def parseNetworkMessage(self, message):
		len, self.something = self.getObject(message,types.IntType)
		len, self.user = self.getObject(message, types.StringType,len)
		len, self.searchid = self.getObject(message, types.IntType,len)
		len, self.searchterm = self.getObject(message, types.StringType,len)

class NetInfo(ServerMessage):
	""" Information about what nodes have been added/removed in the network """
	def __init__(self):
		pass
	
	def parseNetworkMessage(self, message):
		self.list = {}
		len, num = self.getObject(message,types.IntType)
		for i in range(num):
			len, username = self.getObject(message, types.StringType, len)
			import socket
			len, ip = len+4, socket.inet_ntoa(self.strrev(message[len:len+4]))
			len, port = self.getObject(message, types.IntType,len)
			self.list[username] = (ip,port)

class SearchRequest(ServerMessage):
	""" Search request that arrives through the server"""
	def __init__(self):
		pass
	
	def parseNetworkMessage(self, message):
		len, self.code = 1, ord(message[0])
		len, self.something = self.getObject(message,types.IntType,len)
		len, self.user = self.getObject(message, types.StringType,len)
		len, self.searchid = self.getObject(message, types.IntType,len)
		len, self.searchterm = self.getObject(message, types.StringType,len)
	
class GivePrivileges(ServerMessage):
	""" Give (part) of your privileges to another user on the network """
	def __init__(self, user = None, days = None):
		self.user = user
		self.days = days

	def makeNetworkMessage(self):
		return self.packObject(self.user) + self.packObject(self.days)
