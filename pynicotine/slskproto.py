# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
# Based on code from PySoulSeek, original copyright note:
# Copyright (c) 2001-2003 Alexander Kanavin. All rights reserved.

"""
This module implements SoulSeek networking protocol.
"""

from slskmessages import *
import SocketServer
import socket
import random,  sys, time
if sys.platform == "win32":
	from multiselect import multiselect
import select
import threading
import struct

from errno import EINTR
from utils import _

class Connection:
	"""
	Holds data about a connection. conn is a socket object, 
	addr is (ip,port) pair, ibuf and obuf are input and output buffer,
	init is a PeerInit object (see slskmessages docstrings).
	"""
	def __init__(self, conn = None, addr = None, ibuf = "", obuf = ""):
		self.conn = conn
		self.addr = addr
		self.ibuf = ibuf
		self.obuf = obuf
		self.init = None
	#	self.lastwritelength = 10*1024
		self.lastreadlength = 100*1024

class ServerConnection(Connection):
	def __init__(self, conn = None, addr = None, ibuf = "", obuf = ""):
		Connection.__init__(self, conn, addr, ibuf, obuf)
		self.lastping = time.time()

class PeerConnection(Connection):
	def __init__(self, conn = None, addr = None, ibuf = "", obuf = "", init = None):
		Connection.__init__(self,conn,addr,ibuf,obuf)
		self.filereq = None
		self.filedown = None
		self.fileupl = None
		self.filereadbytes = 0
		self.bytestoread = 0
		self.init = init
		self.piercefw = None
		self.lastactive = time.time()
	
		self.starttime = None # Used for upload bandwidth management
		self.sentbytes2 = 0


class PeerConnectionInProgress:
	""" As all p2p connect()s are non-blocking, this class is used to
	hold data about a connection that is not yet established. msgObj is 
	a message to be sent after the connection has been established.
	"""
	def __init__(self, conn = None, msgObj = None):
		self.conn = conn
		self.msgObj = msgObj
		#self.lastactive = time.time()
		
class SlskProtoThread(threading.Thread):
	""" This is a netwroking thread that actually does all the communication.
	It sends data to the UI thread via a callback function and receives data
	via a Queue object.
	"""
	
	""" Server and peers send each other small binary messages, that start
	with length and message code followed by the actual messsage data. 
	These are the codes."""
	
	servercodes = {
		Login:1,
		SetWaitPort:2,
		GetPeerAddress:3,
		AddUser:5,
		GetUserStatus:7,
		SayChatroom:13,
		JoinRoom:14,
		LeaveRoom:15,
		UserJoinedRoom:16,
		UserLeftRoom:17,
		ConnectToPeer:18,
		MessageUser:22,
		MessageAcked:23,
		FileSearch:26,
		SetStatus:28,
		ServerPing:32,
		SendSpeed:34,
		SharedFoldersFiles:35,
		GetUserStats:36,
		QueuedDownloads:40,
		Relogged:41,
		UserSearch:42,
		AddThingILike:51,
		RemoveThingILike:52,
		Recommendations:54,
		GlobalRecommendations:56,
		UserInterests:57,
		PlaceInLineResponse:60,
		RoomAdded:62,
		RoomRemoved:63,
		RoomList:64,
		ExactFileSearch:65,
		AdminMessage:66,
		GlobalUserList:67,
		TunneledMessage:68,
		PrivilegedUsers:69,
		Msg83:83,
		Msg84:84,
		Msg85:85,
		ParentInactivityTimeout:86,
		SearchInactivityTimeout:87,
		MinParentsInCache:88,
		Msg89:89,
		DistribAliveInterval:90,
		AddToPrivileged:91,
		CheckPrivileges:92,
		CantConnectToPeer:1001,
		HaveNoParent:71,
		SearchRequest:93,
		NetInfo:102,
		WishlistSearch:103,
		WishlistInterval:104,
		SimilarUsers:110,
		ItemRecommendations:111,
		ItemSimilarUsers:112,
		RoomTickerState:113,
		RoomTickerAdd:114,
		RoomTickerRemove:115,
		RoomTickerSet:116,
		AddThingIHate:117,
		RemoveThingIHate:118,
		RoomSearch:120, 
		SendUploadSpeed:121,
		GivePrivileges:123,
		NotifyPrivileges:124,
		AckNotifyPrivileges:125,
		}
		
	peercodes = {
		GetSharedFileList:4,
		SharedFileList:5,
		FileSearchRequest:8,
		FileSearchResult:9,
		UserInfoRequest:15,
		UserInfoReply:16,
		PMessageUser:22,
		FolderContentsRequest:36,
		FolderContentsResponse:37,
		TransferRequest:40,
		TransferResponse:41,
		PlaceholdUpload:42,
		QueueUpload:43,
		PlaceInQueue:44,
		UploadFailed:46,
		QueueFailed:50,
		PlaceInQueueRequest:51,
		UploadQueueNotification:52,
		Msg12547:12547
		}

	distribclasses = {0:DistribAlive,3:DistribSearch}

	
	def __init__(self, ui_callback, queue, config):
		""" ui_callback is a UI callback function to be called with messages 
		list as a parameter. queue is Queue object that holds messages from UI
		thread.
		"""
		threading.Thread.__init__(self) 
		self._ui_callback = ui_callback
		self._queue = queue
		self._want_abort = 0
		self._stopped = 0
		self._config = config
		portrange = config.sections["server"]["portrange"]
		self.serverclasses = {}
		for i in self.servercodes.keys():
			self.serverclasses[self.servercodes[i]]=i
		self.peerclasses = {}
		for i in self.peercodes.keys():
			self.peerclasses[self.peercodes[i]]=i
		self._p = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._p.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
		self._conns = {}
		self._connsinprogress={}
		self._uploadlimit = (self._calcLimitNone, 0)
		self._limits = {}
		self._geoip = None
		listenport = None

		try:
			import GeoIP
			self.geoip = GeoIP.new(GeoIP.GEOIP_STANDARD)
		except ImportError:
			try:
				import _GeoIP
				self.geoip = _GeoIP.new(_GeoIP.GEOIP_STANDARD)
			except ImportError:
				self.geoip = None

		for listenport in range(portrange[0],portrange[1]+1):
			try:
				self._p.bind(('',listenport))
			except socket.error:
				listenport = None
			else:
				self._p.listen(1)
				self._ui_callback([IncPort(listenport)])
				break
		if listenport is not None:
			self.start()
	
	def _isUpload(self, conn):
		return conn.__class__ is PeerConnection and conn.fileupl is not None
	
	def _calcUploadSpeed(self, i):
		curtime = time.time()
		if i.starttime is None:
			i.starttime = curtime
		elapsed = curtime - i.starttime
		if elapsed == 0:
			return 0
		else:
			return i.sentbytes2 / elapsed

	def _calcLimitByTransfer(self, conns, i):
		max = self._uploadlimit[1] * 1024.0
		limit = max - self._calcUploadSpeed(i) + 1024
		if limit < 1024.0:
			return 0
		return long(limit)

	def _calcLimitByTotal(self, conns, i):
		max = self._uploadlimit[1] * 1024.0
		bw = 0.0
		for j in conns.values():
			if self._isUpload(j):
				bw = bw + self._calcUploadSpeed(j)
		limit = max - bw + 1024
		if limit < 1024.0:
			return 0
		return long(limit)
	
	def _calcLimitNone(self, conns, i):
		return None
	
	def run(self):
		""" Actual networking loop is here."""
		# @var p Peer / Listen Port
		p = self._p
		# @var s Server Port
		self._s = s = None
		conns = self._conns
		connsinprogress = self._connsinprogress
		queue = self._queue
		
		while not self._want_abort:
			if not queue.empty():
				conns, connsinprogress, s = self.process_queue(queue, conns, connsinprogress,s)
				self._s = s
			for i in conns.keys()[:]:
				if conns[i].__class__ is ServerConnection and i is not s:
					del conns[i]
			outsocks = [i for i in conns.keys() if len(conns[i].obuf) > 0 or (i is not s and conns[i].fileupl is not None and conns[i].fileupl.offset is not None)]
			outsock = []
			self._limits = {}
			for i in outsocks:
				if self._isUpload(conns[i]):
					limit = self._uploadlimit[0](conns, conns[i])
					if limit is None or limit > 0:
						self._limits[i] = limit
						outsock.append(i)
				else:
					outsock.append(i)
			try:
				# Select Networking Input and Output sockets
				if sys.platform == "win32":
					input,output,exc = multiselect(conns.keys() + connsinprogress.keys()+ [p], connsinprogress.keys() + outsock,[], 0.5)
				else:
					input,output,exc = select.select(conns.keys() + connsinprogress.keys() +[p], connsinprogress.keys() + outsock,[], 0.5)
				#print "Sockets open:", len(conns.keys()+connsinprogress.keys()+[p]+outsock), len(conns.keys()),  len(connsinprogress.keys())
			except select.error, error:
				if len(error.args) == 2 and error.args[0] == EINTR:
					# Error recieved; but we don't care :)
					continue
				# Error recieved; terminate networking loop
				print error
				self._want_abort = 1
				self._ui_callback([_("Major Socket Error: Networking terminated! %s" % str(error)) ])
			# Write Output
			for i in conns.keys():
				if i in output:
					try:
						self.writeData(s,conns,i)
					except socket.error, err:
						self._ui_callback([ConnectError(conns[i],err)])
			# Listen / Peer Port
			if p in input[:]:
				try:
					incconn, incaddr = p.accept()
				except:
					time.sleep(0.1)
				else:
					ip, port = self.getIpPort(incaddr)
					if self.ipBlocked(ip):
						self._ui_callback(["ignore connection request from blocked ip address %s %s" %( ip, port)])
						pass
					else:
						conns[incconn] = PeerConnection(incconn,incaddr,"","")
						self._ui_callback([IncConn(incconn, incaddr)])
					
			# Manage Connections
			curtime = time.time()
			for i in connsinprogress.keys()[:]:
				try:
					msgObj = connsinprogress[i].msgObj
					if i in input:
						i.recv(0)
				except socket.error,err:
					self._ui_callback([ConnectError(msgObj,err)])
					del connsinprogress[i]
				else:
					if i in output:
						if i is s:
							conns[s]=ServerConnection(s,msgObj.addr,"","")
							self._ui_callback([ServerConn(s,msgObj.addr)])
						else:
							ip, port = self.getIpPort(msgObj.addr)
							if self.ipBlocked(ip):
								message = "Blocking peer connection in progress to IP: %(ip)s Port: %(port)s" % { "ip":ip, "port":port}
								self._ui_callback([message])
				
							else:
								conns[i]=PeerConnection(i,msgObj.addr,"","",msgObj.init)
								self._ui_callback([OutConn(i,msgObj.addr)])
							
								
						del connsinprogress[i]
					
			# Process Data
			for i in conns.keys()[:]:
				ip, port = self.getIpPort(conns[i].addr)
				if self.ipBlocked(ip) and i is not self._s:
					message = "Blocking peer connection to IP: %(ip)s Port: %(port)s" % { "ip":ip, "port":port}
					print message
					self._ui_callback([message])
					i.close()
					del conns[i]
					continue

				if i in input:
					try:
						self.readData(conns, i)
					except socket.error, err:
						self._ui_callback([ConnectError(conns[i],err)])
				if conns.has_key(i) and len(conns[i].ibuf) > 0:
					if i is s:
						msgs,conns[s].ibuf = self.process_server_input(conns[s].ibuf)
						self._ui_callback(msgs)
					else:
						if conns[i].init is None or conns[i].init.type not in ['F','D']:
							msgs, conns[i] = self.process_peer_input(conns[i],conns[i].ibuf)
							self._ui_callback(msgs)
						if conns[i].init is not None and conns[i].init.type == 'F':
							msgs, conns[i] = self.process_file_input(conns[i],conns[i].ibuf)
							self._ui_callback(msgs)
						if conns[i].init is not None and conns[i].init.type == 'D':
							msgs, conns[i] = self.process_distrib_input(conns[i],conns[i].ibuf)
							self._ui_callback(msgs)
						if conns[i].conn == None:
							del conns[i]

			# ---------------------------
			# Server Pings used to get us banned
			# ---------------------------
			# Timeout Connections
			curtime = time.time()
			connsockets = len(conns.keys())
			for i in conns.keys()[:]:
				if i is not s:
					if curtime - conns[i].lastactive > 120:
					#if connsockets > 60:
						#seconds = 15
					#else:
						#seconds = 30
					#if curtime - conns[i].lastactive > seconds:
						self._ui_callback([ConnClose(i,conns[i].addr)])
						i.close()
						#print "Closed_run", conns[i].addr
						del conns[i]
				else:
					#  Was 30 seconds
					if curtime - conns[s].lastping > 120:
						conns[s].lastping = curtime
						queue.put(ServerPing())
			self._ui_callback([])

		# Close Server Port
		if s is not None:
			s.close()
		self._stopped = 1
		
	def ipBlocked(self, address):
		if address in self._config.sections["server"]["ipblocklist"] or address is None:
			return True
		return False
		
	def getIpPort(self, address):
		ip = port = None
		if type(address) is tuple:
			ip, port = address
		
		return ip, port
		
	def writeData(self, s, conns, i):
		if self._limits.has_key(i):
			limit = self._limits[i]
		else:
			limit = None
	
		conns[i].lastactive = time.time()
		i.setblocking(0)
		if limit is None:
			bytes_send = i.send(conns[i].obuf)
		else:
			bytes_send = i.send(conns[i].obuf[:limit])
		i.setblocking(1)
		conns[i].obuf = conns[i].obuf[bytes_send:]
		if i is not s:
			if conns[i].fileupl is not None and conns[i].fileupl.offset is not None:
				conns[i].fileupl.sentbytes = conns[i].fileupl.sentbytes + bytes_send
				conns[i].sentbytes2 = conns[i].sentbytes2 + bytes_send
				try:
					if conns[i].fileupl.offset + conns[i].fileupl.sentbytes + len(conns[i].obuf) < conns[i].fileupl.size:
						bytestoread = bytes_send*2-len(conns[i].obuf)+10*1024
						if bytestoread > 0:
							read = conns[i].fileupl.file.read(bytestoread)
							conns[i].obuf = conns[i].obuf + read
				except IOError, strerror:
					self._ui_callback([FileError(conns[i],conns[i].fileupl.file, strerror)])
				except ValueError:
					pass
						
				if bytes_send > 0:
					self._ui_callback([conns[i].fileupl])

	def readData(self, conns, i):
		conns[i].lastactive = time.time()
		data = i.recv(conns[i].lastreadlength)
		conns[i].ibuf = conns[i].ibuf + data
		if len(data) >= conns[i].lastreadlength/2:
			conns[i].lastreadlength = conns[i].lastreadlength * 2 
		if not data:
			self._ui_callback([ConnClose(i,conns[i].addr)])
			i.close()
			#print "Closed", conns[i].addr
			del conns[i]


	def process_server_input(self,buffer):
		""" Server has sent us something, this function retrieves messages 
		from the buffer, creates message objects and returns them and the rest 
		of the buffer.
		"""
		msgs=[]
		# Server messages are 8 bytes or greater in length
		while len(buffer) >=8:
			msgsize, msgtype = struct.unpack("<ii",buffer[:8])
			if msgsize + 4 > len(buffer):
				break
			elif self.serverclasses.has_key(msgtype):
				msg = self.serverclasses[msgtype]()
				msg.parseNetworkMessage(buffer[8:msgsize+4])
				msgs.append(msg)
			else:
				msgs.append(_("Server message type %(type)i size %(size)i contents %(buffer)s unknown") %{'type':msgtype, 'size':msgsize-4, 'buffer':buffer[8:msgsize+4].__repr__()})
			buffer = buffer[msgsize+4:]
		return msgs,buffer

	def parseFileReq(self,conn,buffer):
		msg = None
		# File Request messages are 4 bytes or greater in length
		if len(buffer) >= 4:
			reqnum = struct.unpack("<i",buffer[:4])[0]
			msg = FileRequest(conn.conn,reqnum)
			buffer = buffer[4:]
		return msg,buffer

	def parseOffset(self,conn,buffer):
		offset = None
		if len(buffer) >= 8:
			offset = struct.unpack("<i",buffer[:4])[0]
			buffer = buffer[8:]
		return offset,buffer

	def process_file_input(self,conn,buffer):
		""" We have a "F" connection (filetransfer) , peer has sent us 
		something, this function retrieves messages 
		from the buffer, creates message objects and returns them 
		and the rest of the buffer.
		"""
		msgs=[]
		if conn.filereq is None:
			filereq,buffer = self.parseFileReq(conn,buffer)
			if filereq is not None:
				msgs.append(filereq)
				conn.filereq = filereq
		elif conn.filedown is not None:
			leftbytes = conn.bytestoread - conn.filereadbytes
			if leftbytes > 0:
				try:
					conn.filedown.file.write(buffer[:leftbytes])
				except IOError, strerror:
					self._ui_callback([FileError(conn,conn.filedown.file,strerror)])
				except ValueError:
					pass
				self._ui_callback([DownloadFile(conn.conn,len(buffer[:leftbytes]),conn.filedown.file)])
			conn.filereadbytes = conn.filereadbytes + len(buffer[:leftbytes])
			buffer = buffer[leftbytes:]
		elif conn.fileupl is not None:
			if conn.fileupl.offset is None:
				offset,buffer = self.parseOffset(conn,buffer)
				if offset is not None:
					try:
						conn.fileupl.file.seek(offset)
					except IOError, strerror:
						self._ui_callback([FileError(conn,conn.fileupl.file,strerror)])
					except ValueError:
						pass
					conn.fileupl.offset = offset
					self._ui_callback([conn.fileupl])
		    
		conn.ibuf = buffer
		return msgs, conn

	def process_peer_input(self,conn,buffer):
		""" We have a "P" connection (p2p exchange) , peer has sent us 
		something, this function retrieves messages 
		from the buffer, creates message objects and returns them 
		and the rest of the buffer.
		"""
		msgs=[]
		while (conn.init is None or conn.init.type not in ['F','D']) and len(buffer) >= 8:
			msgsize = struct.unpack("<i",buffer[:4])[0]
			if len(buffer) >= 8:
				msgtype = struct.unpack("<i",buffer[4:8])[0]
				self._ui_callback([PeerTransfer(conn,msgsize,len(buffer)-4,self.peerclasses.get(msgtype,None))])
			if msgsize + 4 > len(buffer):
				break
			elif conn.init is None:
				# Unpack Peer Connections
				if buffer[4] == chr(0):
					msg = PierceFireWall(conn)
					try:
						msg.parseNetworkMessage(buffer[5:msgsize+4])
					except Exception, error:
						print error
					else:
						conn.piercefw = msg
						msgs.append(msg)
				elif buffer[4] == chr(1):
					msg = PeerInit(conn)
					try:
						msg.parseNetworkMessage(buffer[5:msgsize+4])
					except Exception, error:
						print error
					else:
						conn.init = msg
						msgs.append(msg)
				elif conn.piercefw is None:
					msgs.append(_("Unknown peer init code: %(type)i, message contents %(buffer)s") %{'type':ord(buffer[4]), 'buffer':buffer[5:msgsize+4].__repr__()})
					conn.conn.close()
					self._ui_callback([ConnClose(conn.conn,conn.addr)])
					conn.conn = None
					break
				else:
					break
			elif conn.init.type == 'P':
				# Unpack Peer Messages
				msgtype = struct.unpack("<i",buffer[4:8])[0]
				if self.peerclasses.has_key(msgtype):
					try: 
						msg = self.peerclasses[msgtype](conn)
						# Parse Peer Message and handle exceptions
						try:
							msg.parseNetworkMessage(buffer[8:msgsize+4])
						except Exception, error:
							host = port = _("unknown")
							msgname = str(self.peerclasses[msgtype]).split(".")[-1]
							print "Error parsing %s:" % msgname, error
							if conn.init.conn.__dict__.has_key("addr"):
								if conn.init.conn.addr is not None:
									host = conn.init.conn.addr[0]
									port = conn.init.conn.addr[1]
							debugmessage = _("There was an error while unpacking Peer message type %(type)s size %(size)i contents %(buffer)s from user: %(user)s, %(host)s:%(port)s") %{'type':msgname, 'size':msgsize-4, 'buffer':buffer[8:msgsize+4].__repr__(), 'user':conn.init.user, 'host': host, 'port': port}
							print debugmessage
							msgs.append(debugmessage)
						else:
							msgs.append(msg)
					except Exception, error:
						print "Error in message function:", error, msgtype, conn
				else:
					host = port = _("unknown")
					if conn.init.conn is not None and conn.init.conn.addr is not None:
						host = conn.init.conn.addr[0]
						port = conn.init.conn.addr[1]
					# Unknown Peer Message
					debugmessage = _("Peer message type %(type)s size %(size)i contents %(buffer)s unknown, from user: %(user)s, %(host)s:%(port)s") %{'type':msgtype, 'size':msgsize-4, 'buffer':buffer[8:msgsize+4].__repr__(), 'user':conn.init.user, 'host': host, 'port': port}
					msgs.append(debugmessage)
					print debugmessage
					
			else:
				# Unknown Message type 
				msgs.append(_("Can't handle connection type %s") %(conn.init.type))
			if msgsize>=0:
				buffer = buffer[msgsize+4:]
			else:
				buffer = ""
		conn.ibuf = buffer
		return msgs,conn

	def process_distrib_input(self, conn, buffer):
		""" We have a distributed network connection, parent has sent us
		something, this function retrieves messages 
		from the buffer, creates message objects and returns them 
		and the rest of the buffer.
		"""
		msgs = []
		while len(buffer) >= 5:
			msgsize = struct.unpack("<i",buffer[:4])[0]
			if msgsize + 4 > len(buffer):
				break
			msgtype = ord(buffer[4])
			if self.distribclasses.has_key(msgtype):
				msg = self.distribclasses[msgtype](conn)
				msg.parseNetworkMessage(buffer[5:msgsize+4])
				msgs.append(msg)
			else:
				msgs.append(_("Distrib message type %(type)i size %(size)i contents %(buffer)s unknown") %{'type':msgtype, 'size':msgsize-1, 'buffer':buffer[5:msgsize+4].__repr__() } )
				conn.conn.close()
				self._ui_callback([ConnClose(conn.conn,conn.addr)])
				conn.conn = None
				break
			if msgsize>=0:
				buffer = buffer[msgsize+4:]
			else:
				buffer = ""
		conn.ibuf = buffer
		return msgs,conn

	def _resetCounters(self, conns):
		curtime = time.time()
		for i in conns.values():
			if self._isUpload(i):
				i.starttime = curtime
				i.sentbytes2 = 0

	def process_queue(self,queue, conns, connsinprogress, s):
		""" Processes messages sent by UI thread. s is a server connection 
		socket object, queue holds the messages, conns ans connsinprogess 
		are dictionaries holding Connection and PeerConnectionInProgress 
		messages."""
		list = []
		needsleep = 0
		while not queue.empty():
			list.append(queue.get())
		for msgObj in list:
			if issubclass(msgObj.__class__,ServerMessage):
				msg = msgObj.makeNetworkMessage()
				if conns.has_key(s):
					conns[s].obuf = conns[s].obuf + struct.pack("<ii",len(msg)+4,self.servercodes[msgObj.__class__]) + msg
				else:
					queue.put(msgObj)
					needsleep = 1
			elif issubclass(msgObj.__class__,PeerMessage):
				if conns.has_key(msgObj.conn):
					# Pack Peer and File and Search Messages 
					if msgObj.__class__ is PierceFireWall:
						conns[msgObj.conn].piercefw = msgObj
						msg = msgObj.makeNetworkMessage()
						conns[msgObj.conn].obuf = conns[msgObj.conn].obuf + struct.pack("<i", len(msg) + 1) + chr(0) + msg
					elif msgObj.__class__ is PeerInit:
						conns[msgObj.conn].init = msgObj
						msg = msgObj.makeNetworkMessage()
						if conns[msgObj.conn].piercefw is None:
							conns[msgObj.conn].obuf = conns[msgObj.conn].obuf + struct.pack("<i", len(msg) + 1) + chr(1) + msg
					
					elif msgObj.__class__ is FileRequest:
						conns[msgObj.conn].filereq = msgObj
						msg = msgObj.makeNetworkMessage()
						conns[msgObj.conn].obuf = conns[msgObj.conn].obuf + msg
						self._ui_callback([msgObj])
					else:
						checkuser = 1
						if msgObj.__class__ is FileSearchResult and msgObj.geoip and self.geoip and self._geoip:
							cc = self.geoip.country_code_by_addr(conns[msgObj.conn].addr[0])
							if not cc and self._geoip[0]:
								checkuser = 0
							elif cc and self._geoip[1][0].find(cc) >= 0:
								checkuser = 0
						if checkuser:
							msg = msgObj.makeNetworkMessage()
							conns[msgObj.conn].obuf = conns[msgObj.conn].obuf + struct.pack("<ii", len(msg) + 4, self.peercodes[msgObj.__class__]) + msg
				else:
					if msgObj.__class__ not in [PeerInit, PierceFireWall, FileSearchResult]:
						#self._ui_callback([Notify(_("Can't send the message over the closed connection: %s %s") %(msgObj.__class__, vars(msgObj)))])
						self._ui_callback([_("Can't send the message over the closed connection: %(type)s %(msg_obj)s") %{'type':msgObj.__class__, 'msg_obj':vars(msgObj)}])
			elif issubclass(msgObj.__class__,InternalMessage):
				if msgObj.__class__ is ServerConn:
					try:
						s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
						s.setblocking(0)
						s.connect_ex(msgObj.addr)
						s.setblocking(1)
						connsinprogress[s]=PeerConnectionInProgress(s,msgObj)
					except socket.error,err:
						self._ui_callback([ConnectError(msgObj,err)])
				elif msgObj.__class__ is ConnClose and conns.has_key(msgObj.conn):
					msgObj.conn.close()
					#print "Close3", conns[msgObj.conn].addr
					self._ui_callback([ConnClose(msgObj.conn,conns[msgObj.conn].addr)])
					del conns[msgObj.conn]
				elif msgObj.__class__ is OutConn:
					try:
						conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
						conn.setblocking(0)
						conn.connect_ex(msgObj.addr)
						conn.setblocking(1)
						connsinprogress[conn]=PeerConnectionInProgress(conn,msgObj)
					except socket.error, (errnum, strerror):
						import errno
						if errno.errorcode.get(errnum,"") == 'EMFILE':
							queue.put(msgObj)
							needsleep = 1
						else:
							self._ui_callback([ConnectError(msgObj,(errnum,strerror))]) 
				elif msgObj.__class__ is DownloadFile and conns.has_key(msgObj.conn):
					conns[msgObj.conn].filedown = msgObj
					conns[msgObj.conn].obuf = conns[msgObj.conn].obuf + struct.pack("<i", msgObj.offset) + struct.pack("<i", 0)
					conns[msgObj.conn].bytestoread = msgObj.filesize - msgObj.offset
					self._ui_callback([DownloadFile(msgObj.conn,0,msgObj.file)])
				elif msgObj.__class__ is UploadFile and conns.has_key(msgObj.conn):
					conns[msgObj.conn].fileupl = msgObj
					self._resetCounters(conns)
				elif msgObj.__class__ is SetGeoBlock:
					self._geoip = msgObj.config
				elif msgObj.__class__ is SetUploadLimit:
					if msgObj.uselimit:
						if msgObj.limitby:
							cb = self._calcLimitByTotal
						else:
							cb = self._calcLimitByTransfer
					else:
						cb = self._calcLimitNone
					self._resetCounters(conns)
					self._uploadlimit = (cb, msgObj.limit)
		if needsleep:
			time.sleep(1)
		
		return conns,connsinprogress,s

	def abort(self):
		""" Call this to abort the thread"""
		self._want_abort = 1 
	
	def stopped(self):
		""" returns true if thread has stopped """
		return self._stopped
