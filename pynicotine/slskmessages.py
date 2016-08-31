# -*- coding: utf-8 -*-
#
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
# Previous copyright below
# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
# Based on code from PySoulSeek, original copyright note:
# Copyright (c) 2001-2003 Alexander Kanavin. All rights reserved.

import struct
import types
import zlib
import hashlib
import os
import sys
from utils import *
from logfacility import log
from itertools import count

""" This module contains message classes, that networking and UI thread
exchange. Basically there are three types of messages: internal messages,
server messages and p2p messages (between clients)."""

counter = count(100)

def newId():
	global counter
	Id = counter.next()
	return Id

# Python objects cannot be used as a source to determine the network object,
# since diff. OS/Arch will have diff. ranges for Integers, Longs, etc.
#
# By default they are all unsigned unless noted otherwise
class NetworkBaseType(object):
	"""Base class for other network types."""
	def __init__(self, value):
		self.value = value

class NetowrkShortIntTye(NetworkBaseType):
	"""Cast to <H, little-endian unsigned short integer (2 bytes)"""
	pass
class NetworkIntType(NetworkBaseType):
	"""Cast to <I, little-endian unsigned integer (4 bytes)"""
	pass
class NetworkSignedIntType(NetworkBaseType):
	"""Cast to <i, little-endian signed integer (4 bytes)"""
	pass
class NetworkLongLongType(NetworkBaseType):
	"""Cast to <Q, little-endian unsigned long long (8 bytes)"""
	pass
class ToBeEncoded(object):
	"""Holds text and the desired eventual encoding"""
	def __init__(self, uni, encoding):
		if type(uni) != type(u""):
			print "ZOMG, you really don't know what you're doing! %s is NOT unicode, its a %s: %s" % (uni, type(uni), repr(uni))
			raise(Exception("Programming bug"))
		self.unicode = uni
		self.encoding = encoding
		self.cached = None
	def getbytes(self):
		if self.cached:
			return self.cached
		self.cached = self.unicode.encode(self.encoding, "replace")
		#print "The bytes of %s are %s" % (self.unicode, repr(self.cached))
		return self.cached
	def dont(self):
		print "Dont do that"
	bytes = property(getbytes, dont)
	def __getitem__(self, key):
		return self.unicode[key]
	def __str__(self):
		return "%s" % (self.getbytes(),)
	def __repr__(self):
		return "ToBeEncoded(%s, %s)" % (repr(self.getbytes()), self.encoding)
class JustDecoded(object):
	"""Holds text, the original bytes and its supposed encoding"""
	def __init__(self, bytes, encoding):
		if type(bytes) != type(""):
			print "ZOMG, you really don't know what you're doing! %s is NOT string, its a %s: %s" % (bytes, type(bytes), repr(bytes))
			raise(Exception("Programming bug"))
		self.bytes = bytes
		self.encoding = encoding
		self.cached = None
		self.modified = False
	def getunicode(self):
		if self.cached:
			return self.cached
		self.cached = self.bytes.decode(self.encoding, "replace")
		return self.cached
	def setunicode(self, uni):
		if type(uni) != type(u""):
			print "ZOMG, you really don't know what you're doing! %s is NOT unicode, its a %s: %s" % (uni, type(uni), repr(bytes))
			raise(Exception("Programming bug"))
		self.cached = uni
	unicode = property(getunicode, setunicode)
	def __getitem__(self, key):
		return self.unicode[key]
	def __str__(self):
		return "%s" % (self.getbytes(),)
	def __repr__(self):
		return "ToBeEncoded(%s, %s)" % (repr(self.getbytes()), self.encoding)

class InternalMessage:
	pass

class ConnectToServer(InternalMessage):
	pass

class Conn(InternalMessage):
	def __init__(self, conn = None, addr = None, init = None):
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
	""" Sent by networking thread to indicate that a file error occurred during
	filetransfer. """
	def __init__(self, conn = None, file = None, strerror = None):
		self.conn = conn
		self.file = file
		self.strerror = strerror

class SetUploadLimit(InternalMessage):
	""" Sent by the GUI thread to indicate changes in bandwidth shaping rules"""
	def __init__(self, uselimit, limit, limitby):
		self.uselimit = uselimit
		self.limit = limit
		self.limitby = limitby

class SetDownloadLimit(InternalMessage):
	""" Sent by the GUI thread to indicate changes in bandwidth shaping rules"""
	def __init__(self, limit):
		self.limit = limit

class SetGeoBlock(InternalMessage):
	""" Sent by the GUI thread to indicate changes in GeoIP blocking"""
	def __init__(self, config):
		self.config = config

class RescanShares(InternalMessage):
	""" Sent by the GUI thread to itself to indicate the need to rescan shares in the background"""
	def __init__(self, shared, yieldfunction):
		self.shared = shared
		self.yieldfunction = yieldfunction
	
class RescanBuddyShares(InternalMessage):
	""" Sent by the GUI thread to itself to indicate the need to rescan shares in the background"""
	def __init__(self, shared, yieldfunction):
		self.shared = shared
		self.yieldfunction = yieldfunction

class DistribConn(InternalMessage):
	def __init__(self):
		pass

class Notify(InternalMessage):
	def __init__(self, msg):
		self.msg = msg

class InternalData(InternalMessage):
	def __init__(self, msg):
		self.msg = msg

class DebugMessage(InternalMessage):
	def __init__(self, msg, debugLevel = None):
		''' debugLevel Options
		0/None - Normal messages and (Human-Readable) Errors
		1 - Warnings & Tracebacks
		2 - Search Results
		3 - Peer Connections
		4 - Message Contents
		5 - Transfers
		6 - Connection, Bandwidth and Usage Statistics
		'''
		self.msg = msg
		self.debugLevel = debugLevel

class SlskMessage:
	""" This is a parent class for all protocol messages. """
	def getObject(self, message, type, start=0, getintasshort=0, getsignedint=0, printerror=True):
		""" Returns object of specified type, extracted from message (which is
		a binary array). start is an offset."""
		intsize = struct.calcsize("<I")
		try:
			if type is types.IntType:
				if getintasshort:
					return intsize+start, struct.unpack("<H", message[start:start+struct.calcsize("<H")])[0]
				elif getsignedint:
					return intsize+start, struct.unpack("<i", message[start:start+intsize])[0]
				else:
					return intsize+start, struct.unpack("<I", message[start:start+intsize])[0]
			elif type is types.LongType:
				if getsignedint:
					return struct.calcsize("<Q")+start, struct.unpack("<Q", message[start:start+struct.calcsize("<Q")])[0]
				else:
					return struct.calcsize("<L")+start, struct.unpack("<L", message[start:start+struct.calcsize("<L")])[0]
			elif type is types.StringType:
				length = struct.unpack("<I", message[start:start+intsize])[0]
				string = message[start+intsize:start+length+intsize]
				return length+intsize+start, string
			elif type is NetworkIntType:
				return intsize+start, struct.unpack("<I", message[start:start+intsize])[0]
			elif type is NetworkSignedIntType:
				return intsize+start, struct.unpack("<i", message[start:start+intsize])[0]
			elif type is NetworkLongLongType:
				return struct.calcsize("<Q")+start, struct.unpack("<Q", message[start:start+struct.calcsize("<Q")])[0]
			else:
				return start, None
		except struct.error, error:
			if printerror:
				log.addwarning("%s %s trying to unpack %s at '%s' at %s/%s" % (self.__class__, error, type, message[start:].__repr__(), start, len(message)))
				self.debug(message)
			raise struct.error, error
			#return start, None

	def packObject(self, object):
		""" Returns object (integer, long or string packed into a 
		binary array."""
		if type(object) is types.IntType:
			return struct.pack("<i", object)
		elif type(object) is types.LongType:
			return struct.pack("<Q", object)
		elif type(object) is types.StringType:
			return struct.pack("<i", len(object))+object
		elif type(object) is ToBeEncoded:
			# The server seeems to cut off strings at \x00 regardless of the length
			return struct.pack("<i", len(object.bytes))+object.bytes
		elif type(object) is types.UnicodeType:
			log.addwarning(_("Warning: networking thread has to convert unicode string %(object)s message %(type)s") % {'object':object, 'type':self.__class__})
			encoded = object.encode("utf-8",'replace')
			return struct.pack("<i", len(encoded))+encoded
		elif type(object) is NetworkIntType:
			return struct.pack("<I", object.value)
		elif type(object) is NetworkSignedIntType:
			return struct.pack("<i", object.value)
		elif type(object) is NetworkLongLongType:
			return struct.pack("<Q", object.value)
		log.addwarning(_("Warning: unknown object type %s") % type(object) +" "+ ("in message %(type)s") % {'type':self.__class__})
		return ""
        
	def makeNetworkMessage(self):
		""" Returns binary array, that can be sent over the network"""
		log.addwarning(_("Empty message made, class %s") % (self.__class__,))
		return None
    
	def parseNetworkMessage(self, message):
		""" Extracts information from the message and sets up fields 
		in an object"""
		log.addwarning(_("Can't parse incoming messages, class %s") % (self.__class__,))
	def doubleParseNetworkMessage(self, message):
		"""Calls self._parseNetworkMessage first with a NetworkLongLongType, if that fails with NetworkIntType."""
		messagename = str(self)
		try:
			#log.add('Decoding %s with LongLong...' % messagename)
			self._parseNetworkMessage(message, NetworkLongLongType)
		except struct.error, e:
			try:
				#log.add('Decoding %s with Int...' % messagename)
				self._parseNetworkMessage(message, NetworkIntType)
			except struct.error, f:
				lines = []
				lines.append(_("Exception during parsing %(area)s: %(exception)s") % {'area':'first ' + messagename, 'exception':e})
				lines.append(_("Exception during parsing %(area)s: %(exception)s") % {'area':'second ' +messagename, 'exception':f})
				lines.append(_("Offending package: %(bytes)s") % {'bytes':repr(message[:1000])})
				log.addwarning("\n".join(lines))
				return False
		#log.add('Successfully decoded %s' % messagename)
		return True
	
	def strrev(self, str):
		strlist = list(str)
		strlist.reverse()
		return ''.join(strlist)
	
	def strunreverse(self, string):
		strlist = string.split(".")
		strlist.reverse()
		return '.'.join(strlist)
	
	def debug(self, message=None):
		print self, self.__dict__
		if message:
			print "Message contents:", message.__repr__()
		
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
		self.ip = None
		
	def makeNetworkMessage(self):

		m = hashlib.md5()
		m.update(self.username+self.passwd)
		md5hash = m.hexdigest()
		message = self.packObject(self.username)+ self.packObject(self.passwd) + self.packObject(self.version) + self.packObject(md5hash) + self.packObject(17)
		#print message.__repr__()
		return message


	def parseNetworkMessage(self, message):
		pos, self.success = 1, ord(message[0])
		if not self.success:
			pos, self.reason = self.getObject(message, types.StringType, pos)
	
		else:
			pos, self.banner = self.getObject(message, types.StringType, pos)
		if len(message[pos:]) > 0 :
			try:
				import socket
				pos, self.ip = pos+4, socket.inet_ntoa(self.strrev(message[pos:pos+4]))
				# Unknown number
			except Exception, error:
				log.addwarning("Error unpacking IP address: %s" % (error,))
			try:
				# MD5 hexdigest of the password you sent
				if len(message[pos:]) > 0:
					pos, self.checksum = self.getObject(message, types.StringType, pos)
				#print self.checksum
			except Exception, error:
				# Not an official client on the official server
				pass

class ChangePassword(ServerMessage):
	""" We sent this to the server to change our password 
	We receive a response if our password changes. """
	
	def __init__(self, password=None):
		self.password = password

	def makeNetworkMessage(self):
		return self.packObject(self.password)

	def parseNetworkMessage(self, message):
		pos, self.password = self.getObject(message, types.StringType)

class SetWaitPort(ServerMessage):
	""" Send this to server to indicate port number that we listen on."""
	def __init__(self, port=None):
		self.port = port
	
	def makeNetworkMessage(self):
		#print "22-" + repr(self.packObject(self.port))
		#print "22+" + repr(self.packObject(NetworkIntType(self.port)))
		return self.packObject(NetworkIntType(self.port))

class GetPeerAddress(ServerMessage):
	""" Used to find out a peer's (ip, port) address."""
	def __init__(self, user = None):
		self.user = user
	
	def makeNetworkMessage(self):
		return self.packObject(self.user)
	
	def parseNetworkMessage(self, message):
		pos, self.user = self.getObject(message, types.StringType)
		import socket
		pos, self.ip = pos+4, socket.inet_ntoa(self.strrev(message[pos:pos+4]))
		pos, self.port = self.getObject(message, types.IntType, pos, 1)
		
class AddUser(ServerMessage):
	""" Used to be kept updated about a user's status."""
	def __init__(self, user = None):
		self.user = user
		self.status = None
		self.avgspeed = None
		self.downloadnum = None
		self.files = None
		self.dirs = None
		self.country = None
		self.privileged = None
		
	def makeNetworkMessage(self):
		return self.packObject(self.user)
	
	def parseNetworkMessage(self, message):
		pos, self.user = self.getObject(message, types.StringType)
		pos, self.userexists = pos+1, ord(message[pos])
		if len(message[pos:]) > 0:
			pos, self.status = self.getObject(message, types.IntType, pos)
			pos, self.avgspeed = self.getObject(message, types.IntType, pos)
			pos, self.downloadnum = self.getObject(message, types.LongType, pos, getsignedint = 1)

			pos, self.files = self.getObject(message, types.IntType, pos)
			pos, self.dirs = self.getObject(message, types.IntType, pos)
			if len(message[pos:]) > 0:
				pos, self.country = self.getObject(message, types.StringType, pos)

class Unknown6(ServerMessage):
	""" Message 6 """
	def __init__(self, user=None):
		self.user = user
	def makeNetworkMessage(self):
		return self.packObject(self.user)
	def parseNetworkMessage(self, message):
		self.debug()
		pass

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

	def parseNetworkMessage(self, message):
		pos, self.user = self.getObject(message, types.StringType)
		pos, self.status = self.getObject(message, types.IntType, pos)
		# Exception handler is for Soulfind compatibility
		try:
			pos, self.privileged = pos+1, ord(message[pos])
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
		
	def parseNetworkMessage(self, message):
		pos, self.token = self.getObject(message, types.IntType)
		pos, self.user = self.getObject(message, types.StringType, pos)
	def makeNetworkMessage(self):
		#print "21-" + repr(self.packObject(self.token))
		#print "21+" + repr(self.packObject(NetworkIntType(self.token)))
		return self.packObject(self.token) + self.packObject(self.user)
	
class AckNotifyPrivileges(ServerMessage):
	def __init__(self, token = None):
		self.token = token
	def parseNetworkMessage(self, message):
		pos, self.token = self.getObject(message, types.IntType)
	def makeNetworkMessage(self):
		#print "20-" + repr(self.packObject(self.token))
		#print "20+" + repr(self.packObject(NetworkIntType(self.token)))
		return self.packObject(NetworkIntType(self.token))
class JoinPublicRoom(ServerMessage):
	"""We want to join the Public Chat"""
	def __init__(self, unknown = 0):
		self.unknown = unknown
	def makeNetworkMessage(self):
		return self.packObject(NetworkIntType(self.unknown))
class LeavePublicRoom(ServerMessage):
	"""We want to leave the Public Chat"""
	def __init__(self, unknown = 0):
		self.unknown = unknown
	def makeNetworkMessage(self):
		return self.packObject(NetworkIntType(self.unknown))
class PublicRoomMessage(ServerMessage):
	"""The server sends us messages from random chatrooms"""
	def parseNetworkMessage(self, message):
		pos, self.room = self.getObject(message, types.StringType)
		pos, self.user = self.getObject(message, types.StringType, pos)
		pos, self.msg = self.getObject(message, types.StringType, pos)
class SayChatroom(ServerMessage):
	""" Either we want to say something in the chatroom, or someone did."""
	def __init__(self, room = None, msg = None):
		self.room = room
		self.msg = msg
	
	def makeNetworkMessage(self):
		return self.packObject(self.room)+self.packObject(self.msg)
	
	def parseNetworkMessage(self, message):
		pos, self.room = self.getObject(message, types.StringType)
		pos, self.user = self.getObject(message, types.StringType, pos)
		pos, self.msg = self.getObject(message, types.StringType, pos)

class UserData:
	""" When we join a room the server send us a bunch of these, 
	for each user."""
	def __init__(self, list):
		self.status = list[0]
		self.avgspeed = list[1]
		self.downloadnum = list[2]
		self.something = list[3]
		self.files = list[4]
		self.dirs = list[5]
		self.slotsfull = list[6]
		self.country = list[7]

class JoinRoom(ServerMessage):
	""" Server sends us this message when we join a room. Contains users list
	with data on everyone."""
	def __init__(self, room = None, private = None):
		self.room = room
		self.private = private
		self.owner = None
		self.operators = []
	def makeNetworkMessage(self):
		if self.private is not None:
			return self.packObject(self.room) + self.packObject(self.private)
		return self.packObject(self.room)
	
	def parseNetworkMessage(self, message):
		pos, self.room = self.getObject(message, types.StringType)
		pos1 = pos
		pos, self.users = self.getUsers(message[pos:])
		pos = pos1 + pos
		
		if len(message[pos:]) > 0:
			self.private=True
			pos, self.owner = self.getObject(message, types.StringType, pos)
		if len(message[pos:]) > 0 and self.private:
			pos, numops = self.getObject(message, types.IntType, pos)
			for i in range(numops):
				pos, operator = self.getObject(message, types.StringType, pos)
				self.operators.append(operator)

	def getUsers(self, message):
		pos, numusers = self.getObject(message, types.IntType)
		users = []
		for i in range(numusers):
			pos, username = self.getObject(message, types.StringType, pos)
			users.append([username, None, None, None, None, None, None, None, None])
		pos, statuslen = self.getObject(message, types.IntType, pos)
		for i in range(statuslen):
			pos, users[i][1] = self.getObject(message, types.IntType, pos)
		pos, statslen = self.getObject(message, types.IntType, pos)
		for i in range(statslen):
			pos, users[i][2] = self.getObject(message, types.IntType, pos, getsignedint=1)
			pos, users[i][3] = self.getObject(message, types.IntType, pos)
			pos, users[i][4] = self.getObject(message, types.IntType, pos)
			pos, users[i][5] = self.getObject(message, types.IntType, pos)
			pos, users[i][6] = self.getObject(message, types.IntType, pos)
		pos, slotslen = self.getObject(message, types.IntType, pos)
		for i in range(slotslen):
			pos, users[i][7] = self.getObject(message, types.IntType, pos)
		if len(message[pos:]) > 0:
			pos, countrylen = self.getObject(message, types.IntType, pos)
			for i in range(countrylen):
				pos, users[i][8] = self.getObject(message, types.StringType, pos)
	
		usersdict={}
		for i in users:
			usersdict[i[0]] = UserData(i[1:])

		return pos, usersdict


class PrivateRoomUsers(ServerMessage):
	""" We get this when we've created a private room."""
	def __init__(self, room = None, numusers = None, users = None):
		self.room = room
		self.numusers = numusers
		self.users = users
		
	def parseNetworkMessage(self, message):
		pos, self.room = self.getObject(message, types.StringType)
		pos, self.numusers = self.getObject(message, types.IntType, pos)
		self.users = []
		for i in range(self.numusers):
			pos, user = self.getObject(message, types.StringType, pos)
			self.users.append(user)
		
class PrivateRoomOwned(ServerMessage):
	""" We get this when we've created a private room."""
	def __init__(self, room = None, number = None):
		self.room = room
		self.number = number
	
	def parseNetworkMessage(self, message):
		pos, self.room = self.getObject(message, types.StringType)
		pos, self.number = self.getObject(message, types.IntType, pos)
		self.operators = []
		for i in range(self.number):
			pos, user = self.getObject(message, types.StringType, pos)
			self.operators.append(user)
		
class PrivateRoomAddUser(ServerMessage):
	""" We get / receive this when we add a user to a private room."""
	def __init__(self, room = None, user = None):
		self.room = room
		self.user = user
	
	def makeNetworkMessage(self):
		return self.packObject(self.room) + self.packObject(self.user)
	
	def parseNetworkMessage(self, message):
		pos, self.room = self.getObject(message, types.StringType)
		pos, self.user = self.getObject(message, types.StringType, pos)
	
class PrivateRoomDismember(ServerMessage):
	""" We do this to remove our own membership of a private room."""
	def __init__(self, room = None):
		self.room = room

	def makeNetworkMessage(self):
		return self.packObject(self.room)
	
	def parseNetworkMessage(self, message):
		pos, self.room = self.getObject(message, types.StringType)
		
class PrivateRoomDisown(ServerMessage):
	""" We do this to stop owning a private room."""
	def __init__(self, room = None):
		self.room = room

	def makeNetworkMessage(self):
		return self.packObject(self.room)
	
	def parseNetworkMessage(self, message):
		pos, self.room = self.getObject(message, types.StringType)
		
class PrivateRoomSomething(ServerMessage):
	"""Unknown"""
	def __init__(self, room = None):
		self.room = room

	def makeNetworkMessage(self):
		return self.packObject(self.room)
	
	def parseNetworkMessage(self, message):
		pos, self.room = self.getObject(message, types.StringType)
		self.debug()
		
class PrivateRoomRemoveUser(ServerMessage):
	""" We get this when we've removed a user from a private room."""
	def __init__(self, room = None, user = None):
		self.room = room
		self.user = user
	
	def makeNetworkMessage(self):
		return self.packObject(self.room) + self.packObject(self.user)
	
	def parseNetworkMessage(self, message):
		pos, self.room = self.getObject(message, types.StringType)
		pos, self.user = self.getObject(message, types.StringType, pos)
		
class PrivateRoomAdded(ServerMessage):
	""" We are sent this when we are added to a private room."""
	def __init__(self, room = None):
		self.room = room
	
	def makeNetworkMessage(self):
		return self.packObject(self.room)
	
	def parseNetworkMessage(self, message):
		self.room = self.getObject(message, types.StringType)[1]
		
class PrivateRoomRemoved(ServerMessage):
	""" We are sent this when we are removed from a private room."""
	def __init__(self, room = None):
		self.room = room
	
	def makeNetworkMessage(self):
		return self.packObject(self.room)
	
	def parseNetworkMessage(self, message):
		self.room = self.getObject(message, types.StringType)[1]
		
class PrivateRoomToggle(ServerMessage):
	""" We send this when we want to enable or disable invitations to private rooms"""
	def __init__(self, enabled = None):
		self.enabled = enabled
	
	def makeNetworkMessage(self):
		return chr(self.enabled)
	
	def parseNetworkMessage(self, message):
		# When this is received, we store it in the config, and disable the appropriate menu item
		pos, self.enabled = 1, bool(ord(message[0]))
		
class PrivateRoomAddOperator(ServerMessage):
	""" We send this to add private room operator abilities to a user"""
	def __init__(self, room = None, user = None):
		self.room = room
		self.user = user
	
	def makeNetworkMessage(self):
		return self.packObject(self.room) + self.packObject(self.user)
	
	def parseNetworkMessage(self, message):
		pos, self.room = self.getObject(message, types.StringType)
		pos, self.user = self.getObject(message, types.StringType, pos)
		
class PrivateRoomRemoveOperator(ServerMessage):
	""" We send this to remove privateroom operator abilities from a user"""
	def __init__(self, room = None, user = None):
		self.room = room
		self.user = user
	
	def makeNetworkMessage(self):
		return self.packObject(self.room) + self.packObject(self.user)
	
	def parseNetworkMessage(self, message):
		pos, self.room = self.getObject(message, types.StringType)
		pos, self.user = self.getObject(message, types.StringType, pos)
		
class PrivateRoomOperatorAdded(ServerMessage):
	""" We receive this when given privateroom operator abilities"""
	def __init__(self, room = None):
		self.room = room
	
	def makeNetworkMessage(self):
		return self.packObject(self.room)
	
	def parseNetworkMessage(self, message):
		pos, self.room = self.getObject(message, types.StringType)
		
class PrivateRoomOperatorRemoved(ServerMessage):
	""" We receive this when privateroom operator abilities are removed"""
	def __init__(self, room = None):
		self.room = room
	
	def makeNetworkMessage(self):
		return self.packObject(self.room)
	
	def parseNetworkMessage(self, message):
		pos, self.room = self.getObject(message, types.StringType)
		#pos, self.username = self.getObject(message, types.StringType, pos)
		
class LeaveRoom(ServerMessage):
	""" We send this when we want to leave a room."""
	def __init__(self, room = None):
		self.room = room
	
	def makeNetworkMessage(self):
		return self.packObject(self.room)
	
	def parseNetworkMessage(self, message):
		self.room = self.getObject(message, types.StringType)[1]


class UserJoinedRoom(ServerMessage):
	""" Server tells us someone has just joined the room."""
	def parseNetworkMessage(self, message):
		pos, self.room = self.getObject(message, types.StringType)
		pos, self.username = self.getObject(message, types.StringType, pos)
		i = [None, None, None, None, None, None, None, None]
		pos, i[0] = self.getObject(message, types.IntType, pos)
		pos, i[1] = self.getObject(message, types.IntType, pos, getsignedint=1)
		for j in range(2, 7):
			pos, i[j] =(self.getObject(message, types.IntType, pos))
		if len(message[pos:]) > 0:
			pos, i[7] = self.getObject(message, types.StringType, pos)
		self.userdata = UserData(i)

class UserLeftRoom(ServerMessage):
	""" Server tells us someone has just left the room."""
	def parseNetworkMessage(self, message):
		pos, self.room = self.getObject(message, types.StringType)
		pos, self.username = self.getObject(message, types.StringType, pos)

class RoomTickerState(ServerMessage):
	""" Message 113 """
	def __init__(self):
		self.room = None
		self.user = None
		self.msgs = {}
	
	def parseNetworkMessage(self, message):
		pos, self.room = self.getObject(message, types.StringType)
		pos, n = self.getObject(message, types.IntType, pos)
		for i in range(n):
			pos, user = self.getObject(message, types.StringType, pos)
			pos, msg = self.getObject(message, types.StringType, pos)
			self.msgs[user] = msg

class RoomTickerAdd(ServerMessage):
	""" Message 114 """
	def __init__(self):
		self.room = None
		self.user = None
		self.msg = None
	
	def parseNetworkMessage(self, message):
		pos, self.room = self.getObject(message, types.StringType)
		pos, self.user = self.getObject(message, types.StringType, pos)
		pos, self.msg = self.getObject(message, types.StringType, pos)

class RoomTickerRemove(ServerMessage):
	""" Message 115 """
	def __init__(self, room = None):
		self.user = None
		self.room = room
	
	def parseNetworkMessage(self, message):
		pos, self.room = self.getObject(message, types.StringType)
		pos, self.user = self.getObject(message, types.StringType, pos)

class RoomTickerSet(ServerMessage):
	""" Message 116 """
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
		return self.packObject(NetworkIntType(self.token))+self.packObject(self.user)+self.packObject(self.type)
	
	def parseNetworkMessage(self, message):
		pos, self.user = self.getObject(message, types.StringType)
		pos, self.type = self.getObject(message, types.StringType, pos)
		import socket
		pos, self.ip = pos+4, socket.inet_ntoa(self.strrev(message[pos:pos+4]))
		pos, self.port = self.getObject(message, types.IntType, pos, 1)
		pos, self.token = self.getObject(message, types.IntType, pos)
		if len(message[pos:]) > 0:
			# Don't know what this is, may be some kind of status
			pos, self.unknown = pos+1, ord(message[pos])

class MessageUser(ServerMessage):
	""" Chat phrase sent to someone or received by us in private"""
	def __init__(self, user = None, msg = None):
		self.user = user
		self.msg = msg
	
	def makeNetworkMessage(self):
		return self.packObject(self.user)+self.packObject(self.msg)
	
	def parseNetworkMessage(self, message):
		pos, self.msgid = self.getObject(message, types.IntType)
		pos, self.timestamp = self.getObject(message, types.IntType, pos)
		pos, self.user = self.getObject(message, types.StringType, pos)
		pos, self.msg = self.getObject(message, types.StringType, pos)
		
class MessageAcked(ServerMessage):
	""" Confirmation of private chat message.
	If we don't send it, the server will keep sending the chat phrase to us.
	"""
	def __init__(self, msgid = None):
		self.msgid = msgid
	
	def makeNetworkMessage(self):
		return self.packObject(NetworkIntType(self.msgid))

class FileSearch(ServerMessage):
	""" We send this to the server when we search for something."""
	""" Server send this to tell us someone is searching for something."""
	def __init__(self, requestid = None, text = None):
		self.searchid = requestid
		self.searchterm = text
		if text:
			self.searchterm = ' '.join([x for x in text.split() if x != '-'])
	
	def makeNetworkMessage(self):
		return self.packObject(NetworkIntType(self.searchid))+self.packObject(self.searchterm)
	
	def parseNetworkMessage(self, message):
		pos, self.user = self.getObject(message, types.StringType)
		pos, self.searchid = self.getObject(message, types.IntType, pos)
		pos, self.searchterm = self.getObject(message, types.StringType, pos)
				
class WishlistSearch(FileSearch):
	pass

class QueuedDownloads(ServerMessage):
	""" Server sends this to indicate if someone has download slots available 
	or not. """
	def parseNetworkMessage(self, message):
		pos, self.user = self.getObject(message, types.StringType)
		pos, self.slotsfull = self.getObject(message, types.IntType, pos)

class SendSpeed(ServerMessage):
	""" We used to send this after a finished download to let the server update
	the speed statistics for a user"""
	def __init__(self, user = None, speed = None):
		self.user = user
		self.speed = speed
	
	def makeNetworkMessage(self):
		print "14-" + repr(self.packObject(self.user)+self.packObject(self.speed))
		print "14+" + repr(self.packObject(self.user)+self.packObject(NetworkIntType(self.speed)))
		return self.packObject(self.user)+self.packObject(NetworkIntType(self.speed))

class SendUploadSpeed(ServerMessage):
	""" We now send this after a finished upload to let the server update
	the speed statistics for a user"""
	def __init__(self, speed = None):
		self.speed = speed
	
	def makeNetworkMessage(self):
		return self.packObject(NetworkIntType(self.speed))
    
class SharedFoldersFiles(ServerMessage):
	""" We send this to server to indicate the number of folder and files
	that we share """
	def __init__(self, folders = None, files = None):
		self.folders = folders
		self.files = files
	
	def makeNetworkMessage(self):
		return self.packObject(NetworkIntType(self.folders))+self.packObject(NetworkIntType(self.files))

class GetUserStats(ServerMessage):
	""" Server sends this to indicate change in user's statistics"""
	def __init__(self, user = None):
		self.user = user
		self.country = None
		
	def makeNetworkMessage(self):
		return self.packObject(self.user)
	
	def parseNetworkMessage(self, message):
		pos, self.user = self.getObject(message, types.StringType)
		pos, self.avgspeed = self.getObject(message, types.IntType, pos, getsignedint = 1)
		pos, self.downloadnum = self.getObject(message, types.LongType, pos, getsignedint = 1)
		pos, self.files = self.getObject(message, types.IntType, pos)
		pos, self.dirs = self.getObject(message, types.IntType, pos)

class Relogged(ServerMessage):
	""" Message 41 """
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
		print "11-" + repr(self.packObject(self.user)+self.packObject(self.req)+self.packObject(self.place))
		print "11+" + repr(self.packObject(self.user)+self.packObject(NetworkIntType(self.req))+self.packObject(NetworkIntType(self.place)))
		return self.packObject(self.user)+self.packObject(NetworkIntType(self.req))+self.packObject(NetworkIntType(self.place))
	
	def parseNetworkMessage(self, message):
		pos, self.user = self.getObject(message, types.StringType)
		pos, self.req = self.getObject(message, types.IntType, pos)
		pos, self.place = self.getObject(message, types.IntType, pos)
		#print self.user, self.req, self.place

class RoomAdded(ServerMessage):
	""" Server tells us a new room has been added"""
	def parseNetworkMessage(self, message):
		self.room = self.getObject(message, types.StringType)[1]

class RoomRemoved(ServerMessage):
	""" Server tells us a room has been removed"""
	def parseNetworkMessage(self, message):
		self.room = self.getObject(message, types.StringType)[1]

class RoomList(ServerMessage):
	""" Server tells us a list of rooms"""
	def __init__(self):
		pass
	
	def makeNetworkMessage(self):
		return ""
	
	def parseNetworkMessage(self, message):
		pos, numrooms = self.getObject(message, types.IntType)
		self.rooms = []
		self.ownedprivaterooms = []
		self.otherprivaterooms = []
		for i in range(numrooms):
			pos, room = self.getObject(message, types.StringType, pos)
			self.rooms.append([room, None])
		pos, numusercounts = self.getObject(message, types.IntType, pos)
		for i in range(numusercounts):
			pos, usercount = self.getObject(message, types.IntType, pos)
			self.rooms[i][1] = usercount
		if len(message[pos:]) == 0:
			return
		(pos, self.ownedprivaterooms) = self._getRooms(pos, message)
		(pos, self.otherprivaterooms) = self._getRooms(pos, message)

	def _getRooms(self, originalpos, message):
		try:
			pos, numberofrooms = self.getObject(message, types.IntType, originalpos)
			rooms = []
			for i in range(numberofrooms):
				pos, room = self.getObject(message, types.StringType, pos)
				rooms.append([room, None])
			pos, numberofusers = self.getObject(message, types.IntType, pos)
			for i in range(numberofusers):
				pos, usercount = self.getObject(message, types.IntType, pos)
				rooms[i][1] = usercount
			return (pos, rooms)
		except Exception, error:
			log.addwarning(_("Exception during parsing %(area)s: %(exception)s") % {'area':'RoomList', 'exception':error})
			return (originalpos, [])

class ExactFileSearch(ServerMessage):
	""" Someone is searching for a file with an exact name """
	def parseNetworkMessage(self, message):
		pos, self.user = self.getObject(message, types.StringType)
		pos, self.req = self.getObject(message, types.IntType, pos)
		pos, self.file = self.getObject(message, types.StringType, pos)
		pos, self.folder = self.getObject(message, types.StringType, pos)
		pos, self.size = self.getObject(message, types.LongType, pos, getsignedint = 1)
		pos, self.checksum = self.getObject(message, types.IntType, pos)

class AdminMessage(ServerMessage):
	""" A global message from the admin has arrived """
	def parseNetworkMessage(self, message):
		self.msg = self.getObject(message, types.StringType)[1]

class GlobalUserList(JoinRoom):
	""" We send this to get a global list of all users online """
	def __init__(self):
		pass
	
	def makeNetworkMessage(self):
		return ""
	
	def parseNetworkMessage(self, message):
		pos, self.users = self.getUsers(message)


class TunneledMessage(ServerMessage):
	def __init__(self, user = None, req = None, code = None, msg = None):
		self.user = user
		self.req = req
		self.code = code
		self.msg = msg
	
	def makeNetworkMessage(self, message):
		print "10-" + repr(self.packObject(self.req)+self.packObject(self.code))
		print "10+" + repr(self.packObject(NetworkInttype(self.req))+self.packObject(NetworkIntType(self.code)))
		return (self.packObject(self.user) +
		        self.packObject(NetworkInttype(self.req)) +
		        self.packObject(NetworkIntType(self.code)) +
		        self.packObject(self.msg))

	def parseNetworkMessage(self, message):
		pos, self.user = self.getObject(message, types.StringType)
		pos, self.code = self.getObject(message, types.IntType, pos)
		pos, self.req = self.getObject(message, types.IntType, pos)
		pos, ip = pos+4, socket.inet_ntoa(self.strrev(message[pos:pos+4]))
		pos, port = self.getObject(message, types.IntType, pos, 1)
		self.addr = (ip, port)
		pos, self.msg = self.getObject(message, types.StringType, pos)

class ParentMinSpeed(ServerMessage):
	""" Message 83 """
	def __init__(self):
		pass
	
	def parseNetworkMessage(self, message):
		pos, self.num = self.getObject(message, types.IntType)

class ParentSpeedRatio(ParentMinSpeed):
	""" Message 84 """
	def __init__(self):
		pass
	
	def parseNetworkMessage(self, message):
		pos, self.num = self.getObject(message, types.IntType)

class SearchParent(ServerMessage):
	""" Message 73 """
	def __init__(self, parentip = None):
		self.parentip = parentip
	
	def makeNetworkMessage(self):
		import socket
		ip = socket.inet_aton(self.strunreverse(self.parentip))
		return self.packObject(ip)

class Msg85(ServerMessage):
	pass


class ParentInactivityTimeout(ServerMessage):
	# 86
	def __init__(self):
		pass
	
	def parseNetworkMessage(self, message):
		pos, self.seconds = self.getObject(message, types.IntType)

class SearchInactivityTimeout(ServerMessage):
	# 87
	def __init__(self):
		pass
	
	def parseNetworkMessage(self, message):
		pos, self.seconds = self.getObject(message, types.IntType)

class MinParentsInCache(ServerMessage):
	def __init__(self):
		pass
	
	def parseNetworkMessage(self, message):
		pos, self.num = self.getObject(message, types.IntType)

class Msg12547(ServerMessage):
	def __init__(self, conn):
		self.conn = conn
		
	def parseNetworkMessage(self, message):
		pass

class UploadQueueNotification(PeerMessage):
	def __init__(self, conn):
		self.conn = conn
	
	def makeNetworkMessage(self):
		return ""
	
	def parseNetworkMessage(self, message):
		return ""

    
class Msg89(ServerMessage):
	def __init__(self):
		pass
		
	def parseNetworkMessage(self, message):
		pass

class DistribAliveInterval(ServerMessage):
	""" Message 90 """
	def __init__(self):
		pass
	
	def parseNetworkMessage(self, message):
		pos, self.seconds = self.getObject(message, types.IntType)


class WishlistInterval(ServerMessage):
	""" Message 104"""
	def __init__(self):
		pass
		
	def parseNetworkMessage(self, message):
		pos, self.seconds = self.getObject(message, types.IntType)

class PrivilegedUsers(ServerMessage):
	""" Message 69 """
	""" A list of those who made a donation """
	def __init__(self):
		pass
	
	def parseNetworkMessage(self, message):
		try:
			x = zlib.decompress(message)
			message =  x[4:]
		except Exception, error:
			pass
		self.users = []
		pos, numusers = self.getObject(message, types.IntType)
		for i in range(numusers):
			pos, user = self.getObject(message, types.StringType, pos)
			self.users.append(user)

class CheckPrivileges(ServerMessage):
	""" Message 92 """
	def __init__(self):
		pass
	
	def makeNetworkMessage(self):
		return ""
	
	def parseNetworkMessage(self, message):
		pos, self.seconds = self.getObject(message, types.IntType)

class AddToPrivileged(ServerMessage):
	""" Message 91 """
	def __init__(self):
		pass
	
	def parseNetworkMessage(self, message):
		l2, self.user = self.getObject(message, types.StringType)

class CantConnectToPeer(ServerMessage):
	""" Message 1001 """
	""" We send this to say we can't connect to peer after it has asked us
	to connect. We receive this if we asked peer to connect and it can't do
	this. So this message means a connection can't be established either way.
	"""
	def __init__(self, token = None, user = None):
		self.token = token
		self.user = user
	
	def makeNetworkMessage(self):
		#X print "9-" + repr(self.packObject(self.token))
		#X print "9+" + repr(self.packObject(NetworkIntType(self.token)))
		return (self.packObject(NetworkIntType(self.token)) + 
		        self.packObject(self.user))
	
	def parseNetworkMessage(self, message):
		pos, self.token = self.getObject(message, types.IntType)

#class CantCreateRoom(ServerMessage):
	#""" Server tells us a new room cannot be created"""
	#def parseNetworkMessage(self, message):
		#self.room = self.getObject(message, types.StringType)[1]

class ServerPing(ServerMessage):
	""" Message 32 """
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

class UserInterests(ServerMessage):
	def __init__(self, user = None):
		self.user = user
		self.likes = None
		self.hates = None
		
	def makeNetworkMessage(self):
		# Request a users' interests
		return self.packObject(self.user)
	
	def parseNetworkMessage(self, message, pos=0):
		# Receive a users' interests
		pos, self.user = self.getObject(message, types.StringType, pos)
		pos, likesnum = self.getObject(message, types.IntType, pos)
		self.likes = []
		for i in range(likesnum):
			pos, key = self.getObject(message, types.StringType, pos)
			self.likes.append(key)
		
		pos, hatesnum = self.getObject(message, types.IntType, pos)
		self.hates = []
		for i in range(hatesnum):
			pos, key = self.getObject(message, types.StringType, pos)
			self.hates.append(key)

class GlobalRecommendations(ServerMessage):
	def __init__(self):
		self.recommendations = None
		self.unrecommendations = None
	
	def makeNetworkMessage(self):
		return ""
	
	def parseNetworkMessage(self, message):
		self.unpack_recommendations(message)
	
	def unpack_recommendations(self, message, pos = 0):
		self.recommendations = {}
		self.unrecommendations = {}
		pos, num = self.getObject(message, types.IntType, pos)
		for i in range(num):
			pos, key = self.getObject(message, types.StringType, pos)
			pos, rating = self.getObject(message, types.IntType, pos, getsignedint=1)
			self.recommendations[key] = rating

		if len(message[pos:]) == 0:
			return
		
		pos, num2 = self.getObject(message, types.IntType, pos)
		for i in range(num2):
			pos, key = self.getObject(message, types.StringType, pos)
			pos, rating = self.getObject(message, types.IntType, pos, getsignedint=1)
			self.unrecommendations[key] = rating
			
class Recommendations(GlobalRecommendations):
	pass
    
class ItemRecommendations(GlobalRecommendations):
	def __init__(self, thing = None):
		GlobalRecommendations.__init__(self)
		self.thing = thing
	
	def makeNetworkMessage(self):
		return self.packObject(self.thing)
	
	def parseNetworkMessage(self, message):
		pos, self.thing = self.getObject(message, types.StringType)
		self.unpack_recommendations(message, pos)

class SimilarUsers(ServerMessage):
	def __init__(self):
		self.users = None
	
	def makeNetworkMessage(self):
		return ""
	
	def parseNetworkMessage(self, message):
		self.users = {}
		pos, num = self.getObject(message, types.IntType)
		for i in range(num):
			pos, user = self.getObject(message, types.StringType, pos)
			pos, rating = self.getObject(message, types.IntType, pos)
			self.users[user] = rating
		
class ItemSimilarUsers(ServerMessage):
	def __init__(self, thing = None):
		self.thing = thing
		self.users = None
	
	def makeNetworkMessage(self):
		return self.packObject(self.thing)
	
	def parseNetworkMessage(self, message):
		self.users = []
		pos, self.thing = self.getObject(message, types.StringType)
		pos, num = self.getObject(message, types.IntType, pos)
		for i in range(num):
			pos, user = self.getObject(message, types.StringType, pos)
			self.users.append(user)

class RoomSearch(ServerMessage):
	def __init__(self, room=None, requestid = None, text = None):
		self.room = room
		self.searchid = requestid
		self.searchterm = text
		if text:
			self.searchterm = ' '.join([x for x in text.split() if x != '-'])
	
	def makeNetworkMessage(self):
		print "8-" + repr(self.packObject(self.searchid))
		print "8+" + repr(self.packObject(NetworkIntType(self.searchid)))
		return (self.packObject(self.room) + 
		        self.packObject(NetworkIntType(self.searchid)) +
		        self.packObject(self.searchterm))
	
	def parseNetworkMessage(self, message):
		pos, self.room = self.getObject(message, types.StringType)
		pos, self.searchid = self.getObject(message, types.IntType, pos)
		pos, self.searchterm = self.getObject(message, types.StringType, pos)
	def __repr__(self):
		return "RoomSearch(room=%s, requestid=%s, text=%s)" % (self.room, self.searchid, self.searchterm)

class UserSearch(ServerMessage):
	def __init__(self, user=None, requestid = None, text = None):
		self.suser = user
		self.searchid = requestid
		self.searchterm = text
	
	def makeNetworkMessage(self):
		print "7-" + repr(self.packObject(self.searchid))
		print "7+" + repr(self.packObject(NetworkIntType(self.searchid)))
		return (self.packObject(self.suser) +
		        self.packObject(NetworkIntType(self.searchid)) +
		        self.packObject(self.searchterm))
	
	def parseNetworkMessage(self, message):
		pos, self.user = self.getObject(message, types.StringType)
		pos, self.searchid = self.getObject(message, types.IntType, pos)
		pos, self.searchterm = self.getObject(message, types.StringType, pos)


class PierceFireWall(PeerMessage):
	""" This is the very first message send by peer that established a 
	connection, if it has been asked by other peer to do so. Token is taken
	from ConnectToPeer server message."""
	def __init__(self, conn, token = None):
		self.conn = conn
		self.token = token
	
	def makeNetworkMessage(self):
		#X print "6-" + repr(self.packObject(self.token))
		#X print "6+" + repr(self.packObject(NetworkIntType(self.token)))
		return self.packObject(NetworkIntType(self.token))
		
	def parseNetworkMessage(self, message):
		pos, self.token = self.getObject(message, types.IntType)

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
		#X print "5-" + repr(self.packObject(self.token))
		#X print "5+" + repr(self.packObject(NetworkIntType(self.token)))
		return (self.packObject(self.user) + 
		        self.packObject(self.type) + 
		        self.packObject(NetworkIntType(self.token)))
	
	def parseNetworkMessage(self, message):
		pos, self.user = self.getObject(message, types.StringType)
		pos, self.type = self.getObject(message, types.StringType, pos)
		pos, self.token = self.getObject(message, types.IntType, pos)

class PMessageUser(PeerMessage):
	""" Chat phrase sent to someone or received by us in private"""
	def __init__(self, conn = None, user = None, msg = None):
		self.conn = conn
		self.user = user
		self.msg = msg
	
	def makeNetworkMessage(self):
		return (self.packObject(0) +
		        self.packObject(0) +
		        self.packObject(self.user) +
		        self.packObject(self.msg))
	
	def parseNetworkMessage(self, message):
		pos, self.msgid = self.getObject(message, types.IntType)
		pos, self.timestamp = self.getObject(message, types.IntType, pos)
		pos, self.user = self.getObject(message, types.StringType, pos)
		pos, self.msg = self.getObject(message, types.StringType, pos)

class UserInfoRequest(PeerMessage):
	""" Ask other peer to send user information, picture and all."""
	def __init__(self, conn):
		self.conn = conn
	
	def makeNetworkMessage(self):
		return ""
	
	def parseNetworkMessage(self, message):
		pass



class UserInfoReply(PeerMessage):
	""" Peer responds with this, when asked for user information."""
	def __init__(self, conn, descr = None, pic = None, totalupl = None, queuesize = None, slotsavail = None, uploadallowed=None):
		self.conn = conn
		self.descr = descr
		self.pic = pic
		self.totalupl = totalupl
		self.queuesize = queuesize
		self.slotsavail = slotsavail
		self.uploadallowed = uploadallowed
	
	def parseNetworkMessage(self, message):
		pos, self.descr = self.getObject(message, types.StringType)
		pos, self.has_pic = pos+1, message[pos]
		if ord(self.has_pic):
			pos, self.pic = self.getObject(message, types.StringType, pos)
		pos, self.totalupl = self.getObject(message, types.IntType, pos)
		pos, self.queuesize = self.getObject(message, types.IntType, pos)
		pos, self.slotsavail = pos+1, ord(message[pos])
		
		if len(message[pos:]) >= 4:
			pos, self.uploadallowed = self.getObject(message, types.IntType, pos)

	def makeNetworkMessage(self):
		if self.pic is not None:
			pic = chr(1) + self.packObject(self.pic)
		else:
			pic = chr(0)
		#X print "4-" + repr(self.packObject(self.descr) + pic + self.packObject(self.totalupl) + self.packObject(self.queuesize) + chr(self.slotsavail) + self.packObject(self.uploadallowed))
		#X print "4+" + repr(self.packObject(self.descr) + pic + self.packObject(NetworkIntType(self.totalupl)) + self.packObject(NetworkIntType(self.queuesize)) + chr(self.slotsavail) + self.packObject(NetworkIntType(self.uploadallowed)))

		return (self.packObject(self.descr) +
		        pic +
		        self.packObject(NetworkIntType(self.totalupl)) +
		        self.packObject(NetworkIntType(self.queuesize)) +
		        chr(self.slotsavail) +
		        self.packObject(NetworkIntType(self.uploadallowed)))



class SharedFileList(PeerMessage):
	""" Peer responds with this when asked for a filelist."""
	def __init__(self, conn, shares = None):
		self.conn = conn
		self.list = shares
		self.built = None
	def parseNetworkMessage(self, message, nozlib = False):
		if not nozlib:
			try:
				message=zlib.decompress(message)
			except Exception, error:
				log.addwarning(_("Exception during parsing %(area)s: %(exception)s") % {'area':'SharedFileList', 'exception':error})
				self.list={}
				return
		if not self.doubleParseNetworkMessage(message):
			self.list = {}
	def _parseNetworkMessage(self, message, sizetype):
		shares = []
		pos, ndir = self.getObject(message, types.IntType)
		for i in range(ndir):
			pos, directory = self.getObject(message, types.StringType, pos)
			pos, nfiles = self.getObject(message, types.IntType, pos)
			files = []
			for j in range(nfiles):
				pos, code = pos+1, ord(message[pos])
				pos, name = self.getObject(message, types.StringType, pos)
				pos, size = self.getObject(message, sizetype, pos, getsignedint = True, printerror=False)
				if message[pos-1] == '\xff':
					# Buggy SLSK?
					# Some file sizes will be huge if unpacked as a signed
					# LongType, namely somewhere in the area of 17179869 Terabytes.
					# It would seem these files are indeed big, but in the Gigabyte range.
					# The following will undo the damage (and if we fuck up it
					# doesn't matter, it can never be worse than reporting 17
					# exabytes for a single file)
					size = struct.unpack("Q", '\xff'*struct.calcsize("Q"))[0] - size
				pos, ext = self.getObject(message, types.StringType, pos, printerror=False)
				pos, numattr = self.getObject(message, types.IntType, pos, printerror=False)
				attrs = []
				for k in range(numattr):
					pos, attrnum = self.getObject(message, types.IntType, pos, printerror=False)
					pos, attr = self.getObject(message, types.IntType, pos, printerror=False)
					attrs.append(attr)
				files.append([code, name, size, ext, attrs])
			shares.append((directory, files))
		self.list = shares

	def makeNetworkMessage(self, nozlib = 0, rebuild=False):
		# Elaborate hack, to save CPU
		# Store packed message contents in self.built, and use
		# instead of repacking it, unless rebuild is True
		if not rebuild and self.built is not None:
			return self.built
		msg = ""
		msg = msg + self.packObject(len(self.list.keys()))
		for (key, value) in self.list.iteritems():
			msg = msg + self.packObject(key.replace(os.sep,"\\")) + value
		if not nozlib:
			self.built = zlib.compress(msg)
		else:
			self.built = msg
		return self.built
		

class GetSharedFileList(PeerMessage):
	""" Ask the peer for a filelist. """ 
	def __init__(self, conn):
	
		self.conn = conn
	
	def parseNetworkMessage(self, message):
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
		print "2-" + repr(self.packObject(self.requestid)+self.packObject(self.text))
		print "2+" + repr(self.packObject(NetworkIntType(self.requestid))+self.packObject(self.text))
		return self.packObject(NetworkIntType(self.requestid))+self.packObject(self.text)
	
	def parseNetworkMessage(self, message):
		pos, self.searchid = self.getObject(message, types.IntType)
		pos, self.searchterm = self.getObject(message, types.StringType, pos)


class FileSearchResult(PeerMessage):
	""" Peer sends this when it has a file search match."""
	def __init__(self, conn, user = None, geoip = None, token = None, shares = None, fileindex = None, freeulslots = None, ulspeed = None, inqueue = None, fifoqueue = None):
		self.conn = conn
		self.user = user
		self.geoip = geoip
		self.token = token
		self.list = shares
		self.fileindex = fileindex
		self.freeulslots = freeulslots
		self.ulspeed = ulspeed 
		self.inqueue = inqueue
		self.fifoqueue = fifoqueue
		self.pos = 0
	def parseNetworkMessage(self, message):
		message = zlib.decompress(message)
		if not self.doubleParseNetworkMessage(message):
			self.list = {}
	def _parseNetworkMessage(self, message, sizetype):
		self.pos, self.user = self.getObject(message, types.StringType)
		self.pos, self.token = self.getObject(message, types.IntType, self.pos)
		self.pos, nfiles = self.getObject(message, types.IntType, self.pos)
		shares = []
		for i in range(nfiles):
			self.pos, code = self.pos+1, ord(message[self.pos])
			self.pos, name = self.getObject(message, types.StringType, self.pos)
			# suppressing errors with unpacking, can be caused by incorrect sizetype
			self.pos, size = self.getObject(message, sizetype, self.pos, printerror=False)
			self.pos, ext = self.getObject(message, types.StringType, self.pos, printerror=False)
			self.pos, numattr = self.getObject(message, types.IntType, self.pos, printerror=False)
			attrs = []
			if numattr:
				for j in range(numattr):
					self.pos, attrnum = self.getObject(message, types.IntType, self.pos, printerror=False)
					self.pos, attr = self.getObject(message, types.IntType, self.pos, printerror=False)
					attrs.append(attr)
			shares.append([code, name, size, ext, attrs])
		self.list = shares
		self.pos, self.freeulslots = self.pos+1, ord(message[self.pos])
		self.pos, self.ulspeed = self.getObject(message, types.IntType, self.pos, getsignedint=1)
		self.pos, self.inqueue = self.getObject(message, types.IntType, self.pos)
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

		msg = (self.packObject(self.user) + 
		       self.packObject(NetworkIntType(self.token)) + 
		       self.packObject(NetworkIntType(len(filelist))))
		for i in filelist:
			msg += (chr(1) +
			        self.packObject(i[0].replace(os.sep,"\\")) + 
			        self.packObject(NetworkLongLongType(i[1])))
			if i[2] is None:
				# No metadata
				msg += self.packObject('')+self.packObject(0)
			else:
				#FileExtension, NumAttributes, 
				msg += self.packObject("mp3") + self.packObject(3)
				msg += (self.packObject(0) +
				        self.packObject(NetworkIntType(i[2][0])) +
				        self.packObject(1) +
				        self.packObject(NetworkIntType(i[3])) + 
				        self.packObject(2) + 
				        self.packObject(i[2][1]))
		msg += (chr(self.freeulslots) + 
		        self.packObject(NetworkIntType(self.ulspeed)) +
		        self.packObject(NetworkIntType(queuesize)))
		return zlib.compress(msg)

class FolderContentsRequest(PeerMessage):
	""" Ask the peer to send us the contents of a single folder. """
	def __init__(self, conn, directory = None):
		self.conn = conn
		self.dir = directory
	
	def makeNetworkMessage(self):
		return self.packObject(1)+self.packObject(self.dir)
	
	def parseNetworkMessage(self, message):
		pos, self.something = self.getObject(message, types.IntType)
		pos, self.dir = self.getObject(message, types.StringType, pos)

class FolderContentsResponse(PeerMessage):
	""" Peer tells us the contents of a particular folder (with all subfolders)
	""" 
	def __init__(self, conn, directory = None, shares = None):
		self.conn = conn
		self.dir = directory
		self.list = shares
	def parseNetworkMessage(self, message):
		try:
			message = zlib.decompress(message)
		except Exception, error:
			log.addwarning(_("Exception during parsing %(area)s: %(exception)s") % {'area':'FolderContentsResponse', 'exception':error})
			self.list = {}
			return
		if not self.doubleParseNetworkMessage(message):
			self.list = {}
	def _parseNetworkMessage(self, message, sizetype):
		shares = {}
		pos, nfolders = self.getObject(message, types.IntType)
		for h in range(nfolders):
			pos, folder = self.getObject(message, types.StringType, pos)
			shares[folder]={}
			pos, ndir = self.getObject(message, types.IntType, pos)
		
			for i in range(ndir):
				pos, directory = self.getObject(message, types.StringType, pos)
				pos, nfiles = self.getObject(message, types.IntType, pos)
				shares[folder][directory] = []
				for j in range(nfiles):
					pos, code = pos+1, ord(message[pos])
					pos, name = self.getObject(message, types.StringType, pos, printerror=False)
					pos, size = self.getObject(message, sizetype, pos, getsignedint = 1, printerror=False)
					pos, ext = self.getObject(message, types.StringType, pos, printerror=False)
					pos, numattr = self.getObject(message, types.IntType, pos, printerror=False)
					attrs = []
					for k in range(numattr):
						pos, attrnum = self.getObject(message, types.IntType, pos, printerror=False)
						pos, attr = self.getObject(message, types.IntType, pos, printerror=False)
						attrs.append(attr)
					shares[folder][directory].append([code, name, size, ext, attrs])
		self.list = shares

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
	def __init__(self, conn, direction = None, req = None, file = None, filesize = None, realfile = None):
		self.conn = conn
		self.direction = direction
		self.req = req
		self.file = file # virtual file
		self.realfile = realfile
		self.filesize = filesize
	
	def makeNetworkMessage(self):
		msg = self.packObject(self.direction)+self.packObject(self.req)+self.packObject(self.file)
		if self.filesize is not None and self.direction == 1:
			msg = msg + self.packObject(NetworkLongLongType(self.filesize))
		return msg
	
	def parseNetworkMessage(self, message):
		pos, self.direction = self.getObject(message, types.IntType)
		pos, self.req = self.getObject(message, types.IntType, pos)
		pos, self.file = self.getObject(message, types.StringType, pos)
		if self.direction == 1:
			pos, self.filesize = self.getObject(message, types.IntType, pos)

class TransferResponse(PeerMessage):
	""" Response to the TreansferRequest - either we (or other peer) agrees, or 
	tells the reason for rejecting filetransfer. """
	def __init__(self, conn, allowed = None, reason = None, req = None, filesize=None):
		self.conn = conn
		self.allowed = allowed
		self.req = req
		self.reason = reason
		self.filesize = filesize
	
	def makeNetworkMessage(self):
		msg = self.packObject(NetworkIntType(self.req)) + chr(self.allowed)
		if self.reason is not None:
			msg = msg + self.packObject(self.reason)
		if self.filesize is not None:
			msg = msg + self.packObject(NetworkLongLongType(self.filesize))
		return msg
	
	def parseNetworkMessage(self, message):
		pos, self.req = self.getObject(message, types.IntType)
		pos, self.allowed = pos+1, ord(message[pos])
		if message[pos:] != "":
			if self.allowed:
				pos, self.filesize = self.getObject(message, types.IntType, pos)
			else:
				pos, self.reason = self.getObject(message, types.StringType, pos)


class PlaceholdUpload(PeerMessage):
	def __init__(self, conn, file = None):
		self.conn = conn
		self.file = file
	
	def makeNetworkMessage(self):
		return self.packObject(self.file)
	
	def parseNetworkMessage(self, message):
		pos, self.file = self.getObject(message, types.StringType)

class QueueUpload(PlaceholdUpload):
	pass

class UploadFailed(PlaceholdUpload):
	pass

class PlaceInQueue(PeerMessage):
	def __init__(self, conn, filename = None, place = None):
		self.conn = conn
		self.filename = filename
		self.place = place
	
	def makeNetworkMessage(self):
		return self.packObject(self.filename) + self.packObject(NetworkIntType(self.place))
	
	def parseNetworkMessage(self, message):
		pos, self.filename = self.getObject(message, types.StringType)
		pos, self.place = self.getObject(message, types.IntType, pos)

class PlaceInQueueRequest(PlaceholdUpload):
	pass

class QueueFailed(PeerMessage):
	def __init__(self, conn, file = None, reason = None):
		self.conn = conn
		self.file = file
		self.reason = reason
	
	def makeNetworkMessage(self):
		return self.packObject(self.file)+self.packObject(self.reason)
	
	def parseNetworkMessage(self, message):
		pos, self.file = self.getObject(message, types.StringType)
		pos, self.reason = self.getObject(message, types.StringType, pos)


class FileRequest(PeerMessage):
	""" Request a file from peer, or tell a peer that we want to send a file to
	them. """
	def __init__(self, conn, req = None):
		self.conn = conn
		self.req = req
	
	def makeNetworkMessage(self):
		msg = self.packObject(self.req)
		return msg

class HaveNoParent(ServerMessage): #71
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
	def __init__(self, conn):
		self.conn = conn
	def parseNetworkMessage(self, message):
		if not self.doubleParseNetworkMessage(message):
			log.addwarning(u'Hitme')
			return False
	def _parseNetworkMessage(self, message, sizetype):
		pos, self.something = self.getObject(message, sizetype, printerror=False)
		pos, self.user = self.getObject(message, types.StringType, pos, printerror=False)
		pos, self.searchid = self.getObject(message, sizetype, pos, printerror=False)
		pos, self.searchterm = self.getObject(message, types.StringType, pos, printerror=False)

class DistribBranchLevel(DistribMessage):
	def __init__(self, conn):
		self.conn = conn
	
	def parseNetworkMessage(self, message):
		pos, self.value = self.getObject(message, types.IntType)
		#print message.__repr__()

class DistribBranchRoot(DistribMessage):
	def __init__(self, conn):
		self.conn = conn
	
	def parseNetworkMessage(self, message):
		#pos, self.value = self.getObject(message, types.IntType)
		pos, self.user = self.getObject(message, types.StringType)
		#print self.something, self.user

class DistribChildDepth(DistribMessage):
	def __init__(self, conn):
		self.conn = conn
	
	def parseNetworkMessage(self, message):
		pos, self.value = self.getObject(message, types.IntType)
		#print self.something, self.user

class DistribMessage9(DistribMessage):
	def __init__(self, conn):
		self.conn = conn
	
	def parseNetworkMessage(self, message):
		#pos, self.value = self.getObject(message, types.IntType)
		try:
			x = zlib.decompress(message)
		except:
			self.debug()
		#message =  x[4:]
		#pos, self.user = self.getObject(message, types.StringType)
		#self.debug()
		#print self.something, self.user

class BranchLevel(ServerMessage):
	def __init__(self):
		pass
	
	def parseNetworkMessage(self, message):
		pos, self.value = self.getObject(message, types.IntType)
		#print message.__repr__()

class BranchRoot(ServerMessage):
	def __init__(self):
		pass
	
	def parseNetworkMessage(self, message):
		#pos, self.value = self.getObject(message, types.IntType)
		pos, self.user = self.getObject(message, types.StringType)
		#print self.something, self.user

class AcceptChildren(ServerMessage):
	def __init__(self, enabled = None):
		self.enabled = enabled

	def makeNetworkMessage(self):
		return chr(self.enabled)

class ChildDepth(ServerMessage):
	def __init__(self):
		pass
	
	def parseNetworkMessage(self, message):
		pos, self.value = self.getObject(message, types.IntType)


class NetInfo(ServerMessage):
	""" Information about what nodes have been added/removed in the network """
	def __init__(self):
		pass
	
	def parseNetworkMessage(self, message):
		self.list = {}
		pos, num = self.getObject(message, types.IntType)
		for i in range(num):
			pos, username = self.getObject(message, types.StringType, pos)
			import socket
			pos, ip = pos+4, socket.inet_ntoa(self.strrev(message[pos:pos+4]))
			pos, port = self.getObject(message, types.IntType, pos)
			self.list[username] = (ip, port)

class SearchRequest(ServerMessage):
	""" Search request that arrives through the server"""
	def __init__(self):
		pass
	
	def parseNetworkMessage(self, message):
		pos, self.code = 1, ord(message[0])
		pos, self.something = self.getObject(message, types.IntType, pos)
		pos, self.user = self.getObject(message, types.StringType, pos)
		pos, self.searchid = self.getObject(message, types.IntType, pos)
		pos, self.searchterm = self.getObject(message, types.StringType, pos)

class UserPrivileged(ServerMessage):
	""" Discover whether a user is privileged or not """
	def __init__(self, user = None):
		self.user = user
		self.privileged = None

	def makeNetworkMessage(self):
		return self.packObject(self.user)


	def parseNetworkMessage(self, message):
		pos, self.user = self.getObject(message, types.StringType, pos)
		pos, self.privileged = pos+1, bool(ord(message[pos]))


class GivePrivileges(ServerMessage):
	""" Give (part) of your privileges to another user on the network """
	def __init__(self, user = None, days = None):
		self.user = user
		self.days = days

	def makeNetworkMessage(self):
		return self.packObject(self.user) + self.packObject(self.days)

class PopupMessage(object):
	"""For messages that should be shown to the user prominently, for example
	through a popup. Should be used sparsely."""
	def __init__(self, title, message):
		self.title = title
		self.message = message
