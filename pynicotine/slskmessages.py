# Copyright (C) 2020-2021 Nicotine+ Team
# Copyright (C) 2007 daelstorm. All rights reserved.
# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
# Based on code from PySoulSeek, original copyright note:
# Copyright (c) 2001-2003 Alexander Kanavin. All rights reserved.
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

import socket
import struct
import zlib

from itertools import islice

from pynicotine.config import config
from pynicotine.logfacility import log
from pynicotine.utils import debug

""" This module contains message classes, that networking and UI thread
exchange. Basically there are three types of messages: internal messages,
server messages and p2p messages (between clients). """


INT_SIZE = struct.calcsize("<i")
INT64_SIZE = struct.calcsize("<q")

INT_UNPACK = struct.Struct("<i").unpack
UINT_UNPACK = struct.Struct("<I").unpack
UINT64_UNPACK = struct.Struct("<Q").unpack

INT_PACK = struct.Struct("<i").pack
UINT_PACK = struct.Struct("<I").pack
UINT64_PACK = struct.Struct("<Q").pack

SEARCH_TOKENS_ALLOWED = set()


class InternalMessage:
    pass


class Conn(InternalMessage):

    __slots__ = ("conn", "addr", "init")

    def __init__(self, conn=None, addr=None, init=None):
        self.conn = conn
        self.addr = addr
        self.init = init


class ServerConn(Conn):
    """ NicotineCore sends this to make networking thread establish a server connection.
    When a connection is established, networking thread returns an object of this type
    to NicotineCore. """


class PeerConn(Conn):
    """ NicotineCore sends this to make networking thread establish a peer connection.
    When a connection is established, networking thread returns an object of this type
    to NicotineCore. """


class IncConn(Conn):
    """ Sent by networking thread to indicate an incoming connection."""


class ConnClose(InternalMessage):
    """ Sent by networking thread to indicate a connection has been closed."""

    __slots__ = ("conn", "addr", "callback")

    def __init__(self, conn=None, addr=None, callback=True):
        self.conn = conn
        self.addr = addr
        self.callback = callback


class ConnectError(InternalMessage):
    """ Sent when a socket exception occurs. It's up to UI thread to
    handle this."""

    __slots__ = ("connobj", "err")

    def __init__(self, connobj=None, err=None):
        self.connobj = connobj
        self.err = err


class ConnectToPeerTimeout:

    __slots__ = ("conn",)

    def __init__(self, conn):
        self.conn = conn


class IncPort(InternalMessage):
    """ Send by networking thread to tell UI thread the port number client
    listens on."""

    def __init__(self, port=None):
        self.port = port


class PeerTransfer(InternalMessage):
    """ Used to indicate progress of long transfers. """

    __slots__ = ("conn", "total", "bufferlen", "msg")

    def __init__(self, conn=None, total=None, bufferlen=None, msg=None):
        self.conn = conn
        self.bufferlen = bufferlen
        self.total = total
        self.msg = msg


class TransferTimeout:

    __slots__ = ("transfer",)

    def __init__(self, transfer):
        self.transfer = transfer


class CheckDownloadQueue(InternalMessage):
    """ Sent from a timer to the main thread to indicate that stuck downloads
    should be checked. """


class CheckUploadQueue(InternalMessage):
    """ Sent from a timer to the main thread to indicate that the upload queue
    should be checked. """


class DownloadFile(InternalMessage):
    """ Sent by networking thread to indicate file transfer progress.
    Sent by UI to pass the file object to write. """

    __slots__ = ("conn", "file")

    def __init__(self, conn=None, file=None):
        self.conn = conn
        self.file = file


class UploadFile(InternalMessage):

    __slots__ = ("conn", "file", "size", "sentbytes", "offset")

    def __init__(self, conn=None, file=None, size=None, sentbytes=0, offset=None):
        self.conn = conn
        self.file = file
        self.size = size
        self.sentbytes = sentbytes
        self.offset = offset


class FileError(InternalMessage):
    """ Sent by networking thread to indicate that a file error occurred during
    filetransfer. """

    __slots__ = ("conn", "file", "strerror")

    def __init__(self, conn=None, file=None, strerror=None):
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


class SetCurrentConnectionCount(InternalMessage):
    """ Sent by networking thread to update the number of current
    connections shown in the GUI. """

    __slots__ = ("msg",)

    def __init__(self, msg):
        self.msg = msg


class SlskMessage:
    """ This is a parent class for all protocol messages. """

    def get_object(self, message, obj_type, start=0, getsignedint=False, getunsignedlonglong=False):
        """ Returns object of specified type, extracted from message (which is
        a binary array). start is an offset."""

        try:
            if obj_type is int:
                if getsignedint:
                    # little-endian signed integer (4 bytes)
                    return INT_SIZE + start, INT_UNPACK(message[start:start + INT_SIZE])[0]

                if getunsignedlonglong:
                    # little-endian unsigned long long (8 bytes)
                    try:
                        return INT64_SIZE + start, UINT64_UNPACK(message[start:start + INT64_SIZE])[0]

                    except Exception:
                        # Fall back to unsigned integer
                        pass

                # little-endian unsigned integer (4 bytes)
                return INT_SIZE + start, UINT_UNPACK(message[start:start + INT_SIZE])[0]

            if obj_type is bytes:
                length = UINT_UNPACK(message[start:start + INT_SIZE])[0]
                content = message[start + INT_SIZE:start + length + INT_SIZE]

                return length + INT_SIZE + start, content

            if obj_type is str:
                length = UINT_UNPACK(message[start:start + INT_SIZE])[0]
                string = message[start + INT_SIZE:start + length + INT_SIZE]

                try:
                    string = string.decode("utf-8")
                except Exception:
                    # Older clients (Soulseek NS)

                    try:
                        string = string.decode("latin-1")
                    except Exception as error:
                        log.add("Error trying to decode string '%s': %s", (string, error))

                return length + INT_SIZE + start, string

            return start, None

        except struct.error as error:
            log.add("%s %s trying to unpack %s at '%s' at %s/%s",
                    (self.__class__, error, obj_type, message[start:].__repr__(), start, len(message)))
            raise struct.error(error)

    def pack_object(self, obj, signedint=False, unsignedlonglong=False, latin1=False):
        """ Returns object (integer, long or string packed into a
        binary array."""

        if isinstance(obj, int):
            if signedint:
                return INT_PACK(obj)

            if unsignedlonglong:
                return UINT64_PACK(obj)

            return UINT_PACK(obj)

        if isinstance(obj, bytes):
            return UINT_PACK(len(obj)) + obj

        if isinstance(obj, str):
            if latin1:
                try:
                    # Try to encode in latin-1 first for older clients (Soulseek NS)
                    encoded = obj.encode("latin-1")
                except Exception:
                    encoded = obj.encode("utf-8", "replace")
            else:
                encoded = obj.encode("utf-8", "replace")

            return UINT_PACK(len(encoded)) + encoded

        log.add("Warning: unknown object type %(obj_type)s in message %(msg_type)s",
                {'obj_type': type(obj), 'msg_type': self.__class__})

        return b""

    def make_network_message(self):
        """ Returns binary array, that can be sent over the network"""

        log.add("Empty message made, class %s", self.__class__)
        return b""

    def parse_network_message(self, _message):
        """ Extracts information from the message and sets up fields
        in an object"""

        log.add("Can't parse incoming messages, class %s", self.__class__)

    @staticmethod
    def strrev(string):
        strlist = list(string)
        strlist.reverse()
        return ''.join(strlist)

    @staticmethod
    def strunreverse(string):
        strlist = string.split(".")
        strlist.reverse()
        return '.'.join(strlist)

    def debug(self, message=None):
        debug(type(self).__name__, self.__dict__, message.__repr__())


"""
Server Messages
"""


class ServerMessage(SlskMessage):
    """ This is a parent class for all server messages. """


class Login(ServerMessage):
    """ Server code: 1 """
    """ We sent this to the server right after the connection has been
    established. Server responds with the greeting message. """

    def __init__(self, username=None, passwd=None, version=None, minorversion=None):
        self.username = username
        self.passwd = passwd
        self.version = version
        self.minorversion = minorversion
        self.success = None
        self.reason = None
        self.banner = None
        self.ip_address = None
        self.checksum = None

    def make_network_message(self):
        from hashlib import md5

        msg = bytearray()
        msg.extend(self.pack_object(self.username))
        msg.extend(self.pack_object(self.passwd))
        msg.extend(self.pack_object(self.version))

        payload = self.username + self.passwd
        md5hash = md5(payload.encode()).hexdigest()
        msg.extend(self.pack_object(md5hash))

        msg.extend(self.pack_object(self.minorversion))

        return msg

    def parse_network_message(self, message):
        pos, self.success = 1, message[0]

        if not self.success:
            pos, self.reason = self.get_object(message, str, pos)
        else:
            pos, self.banner = self.get_object(message, str, pos)

        if not message[pos:]:
            return

        try:
            pos, self.ip_address = pos + 4, socket.inet_ntoa(message[pos:pos + 4][::-1])

        except Exception as error:
            log.add("Error unpacking IP address: %s", error)

        # MD5 hexdigest of the password you sent
        if message[pos:]:
            pos, self.checksum = self.get_object(message, str, pos)


class SetWaitPort(ServerMessage):
    """ Server code: 2 """
    """ We send this to the server to indicate the port number that we
    listen on (2234 by default). """

    def __init__(self, port=None):
        self.port = port

    def make_network_message(self):
        return self.pack_object(self.port)


class GetPeerAddress(ServerMessage):
    """ Server code: 3 """
    """ We send this to the server to ask for a peer's address
    (IP address and port), given the peer's username. """

    def __init__(self, user=None):
        self.user = user
        self.ip_address = None
        self.port = None

    def make_network_message(self):
        return self.pack_object(self.user)

    def parse_network_message(self, message):
        pos, self.user = self.get_object(message, str)
        pos, self.ip_address = pos + 4, socket.inet_ntoa(message[pos:pos + 4][::-1])
        pos, self.port = self.get_object(message, int, pos, 1)


class AddUser(ServerMessage):
    """ Server code: 5 """
    """ Used to be kept updated about a user's stats. When a user's
    stats have changed, the server sends a GetUserStats response message
    with the new user stats. """

    def __init__(self, user=None):
        self.user = user
        self.userexists = None
        self.status = None
        self.avgspeed = None
        self.uploadnum = None
        self.files = None
        self.dirs = None
        self.country = None
        self.privileged = None

    def make_network_message(self):
        return self.pack_object(self.user)

    def parse_network_message(self, message):
        pos, self.user = self.get_object(message, str)
        pos, self.userexists = pos + 1, message[pos]

        if message[pos:]:
            pos, self.status = self.get_object(message, int, pos)
            pos, self.avgspeed = self.get_object(message, int, pos)
            pos, self.uploadnum = self.get_object(message, int, pos, getunsignedlonglong=True)

            pos, self.files = self.get_object(message, int, pos)
            pos, self.dirs = self.get_object(message, int, pos)

            if message[pos:]:
                pos, self.country = self.get_object(message, str, pos)


class RemoveUser(ServerMessage):
    """ Server code: 6 """
    """ Used when we no longer want to be kept updated about a
    user's stats. """

    def __init__(self, user=None):
        self.user = user

    def make_network_message(self):
        return self.pack_object(self.user)


class GetUserStatus(ServerMessage):
    """ Server code: 7 """
    """ The server tells us if a user has gone away or has returned. """

    def __init__(self, user=None):
        self.user = user
        self.status = None
        self.privileged = None

    def make_network_message(self):
        return self.pack_object(self.user)

    def parse_network_message(self, message):
        pos, self.user = self.get_object(message, str)
        pos, self.status = self.get_object(message, int, pos)

        # Soulfind support
        if message[pos:]:
            pos, self.privileged = pos + 1, message[pos]


class SayChatroom(ServerMessage):
    """ Server code: 13 """
    """ Either we want to say something in the chatroom, or someone else did. """

    def __init__(self, room=None, msg=None):
        self.room = room
        self.msg = msg
        self.user = None

    def make_network_message(self):
        return self.pack_object(self.room) + self.pack_object(self.msg)

    def parse_network_message(self, message):
        pos, self.room = self.get_object(message, str)
        pos, self.user = self.get_object(message, str, pos)
        pos, self.msg = self.get_object(message, str, pos)


class UserData:
    """ When we join a room, the server sends us a bunch of these for each user. """

    __slots__ = ("username", "status", "avgspeed", "uploadnum", "files", "dirs", "slotsfull", "country")

    def __init__(self, username=None, status=None, avgspeed=None, uploadnum=None, files=None, dirs=None,
                 slotsfull=None, country=None):
        self.username = username
        self.status = status
        self.avgspeed = avgspeed
        self.uploadnum = uploadnum
        self.files = files
        self.dirs = dirs
        self.slotsfull = slotsfull
        self.country = country


class JoinRoom(ServerMessage):
    """ Server code: 14 """
    """ We send this message to the server when we want to join a room. If the
    room doesn't exist, it is created.

    Server responds with this message when we join a room. Contains users list
    with data on everyone. """

    def __init__(self, room=None, private=None):
        self.room = room
        self.private = private
        self.owner = None
        self.users = []
        self.operators = []

    def make_network_message(self):
        if self.private is not None:
            return self.pack_object(self.room) + self.pack_object(self.private)

        return self.pack_object(self.room)

    def parse_network_message(self, message):
        pos, self.room = self.get_object(message, str)
        pos1 = pos
        pos, self.users = self.get_users(message[pos:])
        pos = pos1 + pos

        if message[pos:]:
            self.private = True
            pos, self.owner = self.get_object(message, str, pos)

        if message[pos:] and self.private:
            pos, numops = self.get_object(message, int, pos)

            for _ in range(numops):
                pos, operator = self.get_object(message, str, pos)

                self.operators.append(operator)

    def get_users(self, message):
        pos, numusers = self.get_object(message, int)

        users = []
        for i in range(numusers):
            users.append(UserData())
            pos, users[i].username = self.get_object(message, str, pos)

        pos, statuslen = self.get_object(message, int, pos)
        for i in range(statuslen):
            pos, users[i].status = self.get_object(message, int, pos)

        pos, statslen = self.get_object(message, int, pos)
        for i in range(statslen):
            pos, users[i].avgspeed = self.get_object(message, int, pos)
            pos, users[i].uploadnum = self.get_object(message, int, pos, getunsignedlonglong=True)
            pos, users[i].files = self.get_object(message, int, pos)
            pos, users[i].dirs = self.get_object(message, int, pos)

        pos, slotslen = self.get_object(message, int, pos)
        for i in range(slotslen):
            pos, users[i].slotsfull = self.get_object(message, int, pos)

        if message[pos:]:
            pos, countrylen = self.get_object(message, int, pos)
            for i in range(countrylen):
                pos, users[i].country = self.get_object(message, str, pos)

        return pos, users


class LeaveRoom(ServerMessage):
    """ Server code: 15 """
    """ We send this to the server when we want to leave a room. """

    def __init__(self, room=None):
        self.room = room

    def make_network_message(self):
        return self.pack_object(self.room)

    def parse_network_message(self, message):
        _pos, self.room = self.get_object(message, str)


class UserJoinedRoom(ServerMessage):
    """ Server code: 16 """
    """ The server tells us someone has just joined a room we're in. """

    def __init__(self):
        self.room = None
        self.userdata = None

    def parse_network_message(self, message):
        pos, self.room = self.get_object(message, str)

        self.userdata = UserData()
        pos, self.userdata.username = self.get_object(message, str, pos)
        pos, self.userdata.status = self.get_object(message, int, pos)
        pos, self.userdata.avgspeed = self.get_object(message, int, pos)
        pos, self.userdata.uploadnum = self.get_object(message, int, pos, getunsignedlonglong=True)
        pos, self.userdata.files = self.get_object(message, int, pos)
        pos, self.userdata.dirs = self.get_object(message, int, pos)
        pos, self.userdata.slotsfull = self.get_object(message, int, pos)

        if message[pos:]:
            pos, self.userdata.country = self.get_object(message, str, pos)


class UserLeftRoom(ServerMessage):
    """ Server code: 17 """
    """ The server tells us someone has just left a room we're in. """

    def __init__(self):
        self.room = None
        self.username = None

    def parse_network_message(self, message):
        pos, self.room = self.get_object(message, str)
        pos, self.username = self.get_object(message, str, pos)


class ConnectToPeer(ServerMessage):
    """ Server code: 18 """
    """ Either we ask server to tell someone else we want to establish a
    connection with them, or server tells us someone wants to connect with us.
    Used when the side that wants a connection can't establish it, and tries
    to go the other way around (direct connection has failed).
    """

    def __init__(self, token=None, user=None, conn_type=None):
        self.token = token
        self.user = user
        self.conn_type = conn_type
        self.ip_address = None
        self.port = None
        self.privileged = None

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.token))
        msg.extend(self.pack_object(self.user))
        msg.extend(self.pack_object(self.conn_type))

        return msg

    def parse_network_message(self, message):
        pos, self.user = self.get_object(message, str)
        pos, self.conn_type = self.get_object(message, str, pos)
        pos, self.ip_address = pos + 4, socket.inet_ntoa(message[pos:pos + 4][::-1])
        pos, self.port = self.get_object(message, int, pos, 1)
        pos, self.token = self.get_object(message, int, pos)

        # Soulfind support
        if message[pos:]:
            pos, self.privileged = pos + 1, message[pos]


class MessageUser(ServerMessage):
    """ Server code: 22 """
    """ Chat phrase sent to someone or received by us in private. """

    def __init__(self, user=None, msg=None):
        self.user = user
        self.msg = msg
        self.msgid = None
        self.timestamp = None
        self.newmessage = None

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.user))
        msg.extend(self.pack_object(self.msg))

        return msg

    def parse_network_message(self, message):
        pos, self.msgid = self.get_object(message, int)
        pos, self.timestamp = self.get_object(message, int, pos)
        pos, self.user = self.get_object(message, str, pos)
        pos, self.msg = self.get_object(message, str, pos)

        if message[pos:]:
            pos, self.newmessage = pos + 1, message[pos]
        else:
            self.newmessage = 1


class MessageAcked(ServerMessage):
    """ Server code: 23 """
    """ We send this to the server to confirm that we received a private message.
    If we don't send it, the server will keep sending the chat phrase to us.
    """

    def __init__(self, msgid=None):
        self.msgid = msgid

    def make_network_message(self):
        return self.pack_object(self.msgid)


class FileSearch(ServerMessage):
    """ Server code: 26 """
    """ We send this to the server when we search for something. Alternatively,
    the server sends this message outside the distributed network to tell us that
    someone is searching for something, currently used for UserSearch and RoomSearch
    requests.

    The search id is a random number generated by the client and is used to track the
    search results.
    """

    def __init__(self, requestid=None, text=None):
        self.searchid = requestid
        self.searchterm = text
        self.user = None

        if text:
            self.searchterm = ' '.join((x for x in text.split() if x != '-'))

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.searchid))
        msg.extend(self.pack_object(self.searchterm, latin1=True))

        return msg

    def parse_network_message(self, message):
        pos, self.user = self.get_object(message, str)
        pos, self.searchid = self.get_object(message, int, pos)
        pos, self.searchterm = self.get_object(message, str, pos)


class SetStatus(ServerMessage):
    """ Server code: 28 """
    """ We send our new status to the server. Status is a way to define whether
    you're available or busy.

    1 = Away
    2 = Online
    """

    def __init__(self, status=None):
        self.status = status

    def make_network_message(self):
        return self.pack_object(self.status)


class ServerPing(ServerMessage):
    """ Server code: 32 """
    """ We test if the server responds. """
    """ DEPRECATED """

    def make_network_message(self):
        return b""

    def parse_network_message(self, message):
        # Empty message
        pass


class SendConnectToken(ServerMessage):
    """ Server code: 33 """
    """ DEPRECATED """

    def __init__(self, user, token):
        self.user = user
        self.token = token

    def make_network_message(self):
        return self.pack_object(self.user) + self.pack_object(self.token)

    def parse_network_message(self, message):
        pos, self.user = self.get_object(message, str)
        pos, self.token = self.get_object(message, int, pos)


class SendDownloadSpeed(ServerMessage):
    """ Server code: 34 """
    """ We used to send this after a finished download to let the server update
    the speed statistics for a user. """
    """ DEPRECATED """

    def __init__(self, user=None, speed=None):
        self.user = user
        self.speed = speed

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.user))
        msg.extend(self.pack_object(self.speed))

        return msg


class SharedFoldersFiles(ServerMessage):
    """ Server code: 35 """
    """ We send this to server to indicate the number of folder and files
    that we share. """

    def __init__(self, folders=None, files=None):
        self.folders = folders
        self.files = files

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.folders))
        msg.extend(self.pack_object(self.files))

        return msg


class GetUserStats(ServerMessage):
    """ Server code: 36 """
    """ The server sends this to indicate a change in a user's statistics,
    if we've requested to watch the user in AddUser previously. A user's
    stats can also be requested by sending a GetUserStats message to the
    server, but AddUser should be used instead. """

    def __init__(self, user=None):
        self.user = user
        self.avgspeed = None
        self.uploadnum = None
        self.files = None
        self.dirs = None

    def make_network_message(self):
        return self.pack_object(self.user)

    def parse_network_message(self, message):
        pos, self.user = self.get_object(message, str)
        pos, self.avgspeed = self.get_object(message, int, pos)
        pos, self.uploadnum = self.get_object(message, int, pos, getunsignedlonglong=True)
        pos, self.files = self.get_object(message, int, pos)
        pos, self.dirs = self.get_object(message, int, pos)


class QueuedDownloads(ServerMessage):
    """ Server code: 40 """
    """ The server sends this to indicate if someone has download slots available
    or not. """
    """ DEPRECATED """

    def __init__(self):
        self.user = None
        self.slotsfull = None

    def parse_network_message(self, message):
        pos, self.user = self.get_object(message, str)
        pos, self.slotsfull = self.get_object(message, int, pos)


class Relogged(ServerMessage):
    """ Server code: 41 """
    """ The server sends this if someone else logged in under our nickname,
    and then disconnects us. """

    def parse_network_message(self, message):
        # Empty message
        pass


class UserSearch(ServerMessage):
    """ Server code: 42 """
    """ We send this to the server when we search a specific user's shares.
    The ticket/search id is a random number generated by the client and is
    used to track the search results. """

    def __init__(self, user=None, requestid=None, text=None):
        self.user = user
        self.searchid = requestid
        self.searchterm = text

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.user))
        msg.extend(self.pack_object(self.searchid))
        msg.extend(self.pack_object(self.searchterm))

        return msg

    # Soulfind support, the official server sends a FileSearch message (code 26) instead
    def parse_network_message(self, message):
        pos, self.user = self.get_object(message, str)
        pos, self.searchid = self.get_object(message, int, pos)
        pos, self.searchterm = self.get_object(message, str, pos)


class AddThingILike(ServerMessage):
    """ Server code: 51 """
    """ We send this to the server when we add an item to our likes list. """

    def __init__(self, thing=None):
        self.thing = thing

    def make_network_message(self):
        return self.pack_object(self.thing)


class RemoveThingILike(ServerMessage):
    """ Server code: 52 """
    """ We send this to the server when we remove an item from our likes list. """

    def __init__(self, thing=None):
        self.thing = thing

    def make_network_message(self):
        return self.pack_object(self.thing)


class Recommendations(ServerMessage):
    """ Server code: 54 """
    """ The server sends us a list of personal recommendations and a number
    for each. """

    def __init__(self):
        self.recommendations = {}
        self.unrecommendations = {}

    def make_network_message(self):
        return b""

    def parse_network_message(self, message):
        self.unpack_recommendations(message)

    def unpack_recommendations(self, message, pos=0):
        pos, num = self.get_object(message, int, pos)

        for _ in range(num):
            pos, key = self.get_object(message, str, pos)
            pos, rating = self.get_object(message, int, pos, getsignedint=True)

            # The server also includes unrecommendations here for some reason, don't add them
            if rating >= 0:
                self.recommendations[key] = rating

        if not message[pos:]:
            return

        pos, num2 = self.get_object(message, int, pos)

        for _ in range(num2):
            pos, key = self.get_object(message, str, pos)
            pos, rating = self.get_object(message, int, pos, getsignedint=True)

            # The server also includes recommendations here for some reason, don't add them
            if rating < 0:
                self.unrecommendations[key] = rating


class GlobalRecommendations(Recommendations):
    """ Server code: 56 """
    """ The server sends us a list of global recommendations and a number
    for each. """


class UserInterests(ServerMessage):
    """ Server code: 57 """
    """ We ask the server for a user's liked and hated interests. The server
    responds with a list of interests. """

    def __init__(self, user=None):
        self.user = user
        self.likes = []
        self.hates = []

    def make_network_message(self):
        return self.pack_object(self.user)

    def parse_network_message(self, message):
        pos, self.user = self.get_object(message, str)
        pos, likesnum = self.get_object(message, int, pos)

        for _ in range(likesnum):
            pos, key = self.get_object(message, str, pos)

            self.likes.append(key)

        pos, hatesnum = self.get_object(message, int, pos)

        for _ in range(hatesnum):
            pos, key = self.get_object(message, str, pos)

            self.hates.append(key)


class AdminCommand(ServerMessage):
    """ Server code: 58 """

    def __init__(self, string=None, strings=None):
        self.string = string
        self.strings = strings

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.string))
        msg.extend(self.pack_object(len(self.strings)))

        for i in self.strings:
            msg.extend(self.pack_object(i))

        return msg


class PlaceInLineResponse(ServerMessage):
    """ Server code: 60 """
    """ Server sends this to indicate change in place in queue while we're
    waiting for files from other peer. """
    """ DEPRECATED """

    def __init__(self, user=None, req=None, place=None):
        self.req = req
        self.user = user
        self.place = place

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.user))
        msg.extend(self.pack_object(self.req))
        msg.extend(self.pack_object(self.place))

        return msg

    def parse_network_message(self, message):
        pos, self.user = self.get_object(message, str)
        pos, self.req = self.get_object(message, int, pos)
        pos, self.place = self.get_object(message, int, pos)


class RoomAdded(ServerMessage):
    """ Server code: 62 """
    """ The server tells us a new room has been added. """
    """ DEPRECATED """

    def __init__(self):
        self.room = None

    def parse_network_message(self, message):
        _pos, self.room = self.get_object(message, str)


class RoomRemoved(ServerMessage):
    """ Server code: 63 """
    """ The server tells us a room has been removed. """
    """ DEPRECATED """

    def __init__(self):
        self.room = None

    def parse_network_message(self, message):
        _pos, self.room = self.get_object(message, str)


class RoomList(ServerMessage):
    """ Server code: 64 """
    """ The server tells us a list of rooms and the number of users in
    them. When connecting to the server, the server only sends us rooms
    with at least 5 users. A few select rooms are also excluded, such as
    nicotine and The Lobby. Requesting the room list yields a response
    containing the missing rooms. """

    def __init__(self):
        self.rooms = []
        self.ownedprivaterooms = []
        self.otherprivaterooms = []

    def make_network_message(self):
        return b""

    def parse_network_message(self, message):
        pos, numrooms = self.get_object(message, int)

        for i in range(numrooms):
            pos, room = self.get_object(message, str, pos)

            self.rooms.append([room, None])

        pos, numusers = self.get_object(message, int, pos)

        for i in range(numusers):
            pos, usercount = self.get_object(message, int, pos)

            self.rooms[i][1] = usercount

        if not message[pos:]:
            return

        pos, self.ownedprivaterooms = self.get_rooms(pos, message)
        pos, self.otherprivaterooms = self.get_rooms(pos, message)

    def get_rooms(self, originalpos, message):
        try:
            pos, numrooms = self.get_object(message, int, originalpos)

            rooms = []
            for i in range(numrooms):
                pos, room = self.get_object(message, str, pos)

                rooms.append([room, None])

            pos, numusers = self.get_object(message, int, pos)

            for i in range(numusers):
                pos, usercount = self.get_object(message, int, pos)

                rooms[i][1] = usercount

            return (pos, rooms)

        except Exception as error:
            log.add("Exception during parsing %(area)s: %(exception)s", {'area': 'RoomList', 'exception': error})
            return (originalpos, [])


class ExactFileSearch(ServerMessage):
    """ Server code: 65 """
    """ We send this to search for an exact file name and folder,
    to find other sources. """
    """ DEPRECATED (no results even with official client) """

    def __init__(self, req=None, file=None, folder=None, size=None, checksum=None):
        self.req = req
        self.file = file
        self.folder = folder
        self.size = size
        self.checksum = checksum
        self.user = None

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.req))
        msg.extend(self.pack_object(self.file))
        msg.extend(self.pack_object(self.folder))
        msg.extend(self.pack_object(self.size, unsignedlonglong=True))
        msg.extend(self.pack_object(self.checksum))

        return msg

    def parse_network_message(self, message):
        pos, self.user = self.get_object(message, str)
        pos, self.req = self.get_object(message, int, pos)
        pos, self.file = self.get_object(message, str, pos)
        pos, self.folder = self.get_object(message, str, pos)
        pos, self.size = self.get_object(message, int, pos, getunsignedlonglong=True)
        pos, self.checksum = self.get_object(message, int, pos)


class AdminMessage(ServerMessage):
    """ Server code: 66 """
    """ A global message from the server admin has arrived. """

    def __init__(self):
        self.msg = None

    def parse_network_message(self, message):
        _pos, self.msg = self.get_object(message, str)


class GlobalUserList(ServerMessage):
    """ Server code: 67 """
    """ We send this to get a global list of all users online. """
    """ DEPRECATED """

    def __init__(self):
        self.users = None

    def make_network_message(self):
        return b""

    def parse_network_message(self, message):
        _pos, self.users = self.get_users(message)

    def get_users(self, message):
        pos, numusers = self.get_object(message, int)

        users = []
        for i in range(numusers):
            users.append(UserData())
            pos, users[i].username = self.get_object(message, str, pos)

        pos, statuslen = self.get_object(message, int, pos)
        for i in range(statuslen):
            pos, users[i].status = self.get_object(message, int, pos)

        pos, statslen = self.get_object(message, int, pos)
        for i in range(statslen):
            pos, users[i].avgspeed = self.get_object(message, int, pos)
            pos, users[i].uploadnum = self.get_object(message, int, pos, getunsignedlonglong=True)
            pos, users[i].files = self.get_object(message, int, pos)
            pos, users[i].dirs = self.get_object(message, int, pos)

        pos, slotslen = self.get_object(message, int, pos)
        for i in range(slotslen):
            pos, users[i].slotsfull = self.get_object(message, int, pos)

        if message[pos:]:
            pos, countrylen = self.get_object(message, int, pos)
            for i in range(countrylen):
                pos, users[i].country = self.get_object(message, str, pos)

        return pos, users


class TunneledMessage(ServerMessage):
    """ Server code: 68 """
    """ Server message for tunneling a chat message. """
    """ DEPRECATED """

    def __init__(self, user=None, req=None, code=None, msg=None):
        self.user = user
        self.req = req
        self.code = code
        self.msg = msg
        self.addr = None

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.user))
        msg.extend(self.pack_object(self.req))
        msg.extend(self.pack_object(self.code))
        msg.extend(self.pack_object(self.msg))

        return msg

    def parse_network_message(self, message):
        pos, self.user = self.get_object(message, str)
        pos, self.code = self.get_object(message, int, pos)
        pos, self.req = self.get_object(message, int, pos)

        pos, ip_address = pos + 4, socket.inet_ntoa(self.strrev(message[pos:pos + 4]))
        pos, port = self.get_object(message, int, pos, 1)
        self.addr = (ip_address, port)

        pos, self.msg = self.get_object(message, str, pos)


class PrivilegedUsers(ServerMessage):
    """ Server code: 69 """
    """ The server sends us a list of privileged users, a.k.a. users who
    have donated. """

    def __init__(self):
        self.users = None

    def parse_network_message(self, message):
        pos, numusers = self.get_object(message, int)

        self.users = []
        for _ in range(numusers):
            pos, user = self.get_object(message, str, pos)

            self.users.append(user)


class HaveNoParent(ServerMessage):
    """ Server code: 71 """
    """ We inform the server if we have a distributed parent or not.
    If not, the server eventually sends us a PossibleParents message with a
    list of 10 possible parents to connect to. """

    def __init__(self, noparent=None):
        self.noparent = noparent

    def make_network_message(self):
        return bytes([self.noparent])


class SearchParent(ServerMessage):
    """ Server code: 73 """
    """ We send the IP address of our parent to the server. """
    """ DEPRECATED """

    def __init__(self, parentip=None):
        self.parentip = parentip

    def make_network_message(self):
        return self.pack_object(socket.inet_aton(self.strunreverse(self.parentip)))


class ParentMinSpeed(ServerMessage):
    """ Server code: 83 """
    """ UNUSED """

    def __init__(self):
        self.num = None

    def parse_network_message(self, message):
        _pos, self.num = self.get_object(message, int)


class ParentSpeedRatio(ServerMessage):
    """ Server code: 84 """
    """ UNUSED """

    def __init__(self):
        self.num = None

    def parse_network_message(self, message):
        _pos, self.num = self.get_object(message, int)


class ParentInactivityTimeout(ServerMessage):
    """ Server code: 86 """
    """ DEPRECATED """

    def __init__(self):
        self.seconds = None

    def parse_network_message(self, message):
        _pos, self.seconds = self.get_object(message, int)


class SearchInactivityTimeout(ServerMessage):
    """ Server code: 87 """
    """ DEPRECATED """

    def __init__(self):
        self.seconds = None

    def parse_network_message(self, message):
        _pos, self.seconds = self.get_object(message, int)


class MinParentsInCache(ServerMessage):
    """ Server code: 88 """
    """ DEPRECATED """

    def __init__(self):
        self.num = None

    def parse_network_message(self, message):
        _pos, self.num = self.get_object(message, int)


class DistribAliveInterval(ServerMessage):
    """ Server code: 90 """
    """ DEPRECATED """

    def __init__(self):
        self.seconds = None

    def parse_network_message(self, message):
        _pos, self.seconds = self.get_object(message, int)


class AddToPrivileged(ServerMessage):
    """ Server code: 91 """
    """ The server sends us the username of a new privileged user, which we
    add to our list of global privileged users. """
    """ DEPRECATED """

    def __init__(self):
        self.user = None

    def parse_network_message(self, message):
        _pos, self.user = self.get_object(message, str)


class CheckPrivileges(ServerMessage):
    """ Server code: 92 """
    """ We ask the server how much time we have left of our privileges.
    The server responds with the remaining time, in seconds. """

    def __init__(self):
        self.seconds = None

    def make_network_message(self):
        return b""

    def parse_network_message(self, message):
        _pos, self.seconds = self.get_object(message, int)


class EmbeddedMessage(ServerMessage):
    """ Server code: 93 """
    """ The server sends us an embedded distributed message. The only type
    of distributed message sent at present is DistribSearch (distributed code 3).
    If we receive such a message, we are a branch root in the distributed network,
    and we distribute the embedded message (not the unpacked distributed message)
    to our child peers. """

    __slots__ = ("distrib_code", "distrib_message")

    def __init__(self):
        self.distrib_code = None
        self.distrib_message = None

    def parse_network_message(self, message):
        self.distrib_code = message[0]
        self.distrib_message = message[1:]


class AcceptChildren(ServerMessage):
    """ Server code: 100 """
    """ We tell the server if we want to accept child nodes. """

    def __init__(self, enabled=None):
        self.enabled = enabled

    def make_network_message(self):
        return bytes([self.enabled])


class PossibleParents(ServerMessage):
    """ Server code: 102 """
    """ The server send us a list of 10 possible distributed parents to connect to.
    This message is sent to us at regular intervals until we tell the server we don't
    need more possible parents, through a HaveNoParent message. """

    def __init__(self):
        self.list = None

    def parse_network_message(self, message):
        pos, num = self.get_object(message, int)

        self.list = {}
        for _ in range(num):
            pos, username = self.get_object(message, str, pos)
            pos, ip_address = pos + 4, socket.inet_ntoa(message[pos:pos + 4][::-1])
            pos, port = self.get_object(message, int, pos)

            self.list[username] = (ip_address, port)


class WishlistSearch(FileSearch):
    """ Server code: 103 """


class WishlistInterval(ServerMessage):
    """ Server code: 104 """

    def __init__(self):
        self.seconds = None

    def parse_network_message(self, message):
        _pos, self.seconds = self.get_object(message, int)


class SimilarUsers(ServerMessage):
    """ Server code: 110 """
    """ The server sends us a list of similar users related to our interests. """

    def __init__(self):
        self.users = None

    def make_network_message(self):
        return b""

    def parse_network_message(self, message):
        pos, num = self.get_object(message, int)

        self.users = {}
        for _ in range(num):
            pos, user = self.get_object(message, str, pos)
            pos, rating = self.get_object(message, int, pos)

            self.users[user] = rating


class ItemRecommendations(Recommendations):
    """ Server code: 111 """
    """ The server sends us a list of recommendations related to a specific
    item, which is usually present in the like/dislike list or an existing
    recommendation list. """

    def __init__(self, thing=None):
        super().__init__()
        self.thing = thing

    def make_network_message(self):
        return self.pack_object(self.thing)

    def parse_network_message(self, message):
        pos, self.thing = self.get_object(message, str)
        self.unpack_recommendations(message, pos)


class ItemSimilarUsers(ServerMessage):
    """ Server code: 112 """
    """ The server sends us a list of similar users related to a specific item,
    which is usually present in the like/dislike list or recommendation list. """

    def __init__(self, thing=None):
        self.thing = thing
        self.users = None

    def make_network_message(self):
        return self.pack_object(self.thing)

    def parse_network_message(self, message):
        pos, self.thing = self.get_object(message, str)
        pos, num = self.get_object(message, int, pos)

        self.users = []
        for _ in range(num):
            pos, user = self.get_object(message, str, pos)

            self.users.append(user)


class RoomTickerState(ServerMessage):
    """ Server code: 113 """
    """ The server returns a list of tickers in a chat room.

    Tickers are customizable, user-specific messages that appear on
    chat room walls. """

    def __init__(self):
        self.room = None
        self.user = None
        self.msgs = {}

    def parse_network_message(self, message):
        pos, self.room = self.get_object(message, str)
        pos, num = self.get_object(message, int, pos)

        for _ in range(num):
            pos, user = self.get_object(message, str, pos)
            pos, msg = self.get_object(message, str, pos)

            self.msgs[user] = msg


class RoomTickerAdd(ServerMessage):
    """ Server code: 114 """
    """ The server sends us a new ticker that was added to a chat room.

    Tickers are customizable, user-specific messages that appear on
    chat room walls. """

    def __init__(self):
        self.room = None
        self.user = None
        self.msg = None

    def parse_network_message(self, message):
        pos, self.room = self.get_object(message, str)
        pos, self.user = self.get_object(message, str, pos)
        pos, self.msg = self.get_object(message, str, pos)


class RoomTickerRemove(ServerMessage):
    """ Server code: 115 """
    """ The server informs us that a ticker was removed from a chat room.

    Tickers are customizable, user-specific messages that appear on
    chat room walls. """

    def __init__(self):
        self.room = None
        self.user = None

    def parse_network_message(self, message):
        pos, self.room = self.get_object(message, str)
        pos, self.user = self.get_object(message, str, pos)


class RoomTickerSet(ServerMessage):
    """ Server code: 116 """
    """ We send this to the server when we change our own ticker in
    a chat room. Sending an empty ticker string removes any existing
    ticker in the room.

    Tickers are customizable, user-specific messages that appear on
    chat room walls. """

    def __init__(self, room=None, msg=""):
        self.room = room
        self.msg = msg

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.room))
        msg.extend(self.pack_object(self.msg))

        return msg


class AddThingIHate(AddThingILike):
    """ Server code: 117 """
    """ We send this to the server when we add an item to our hate list. """


class RemoveThingIHate(RemoveThingILike):
    """ Server code: 118 """
    """ We send this to the server when we remove an item from our hate list. """


class RoomSearch(ServerMessage):
    """ Server code: 120 """
    """ We send this to the server to search files shared by users who have joined
    a specific chat room. The ticket/search id is a random number generated by the
    client and is used to track the search results. """

    def __init__(self, room=None, requestid=None, text=""):
        self.room = room
        self.searchid = requestid
        self.searchterm = ' '.join([x for x in text.split() if x != '-'])
        self.user = None

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.room))
        msg.extend(self.pack_object(self.searchid))
        msg.extend(self.pack_object(self.searchterm, latin1=True))

        return msg

    # Soulfind support, the official server sends a FileSearch message (code 26) instead
    def parse_network_message(self, message):
        pos, self.user = self.get_object(message, str)
        pos, self.searchid = self.get_object(message, int, pos)
        pos, self.searchterm = self.get_object(message, str, pos)


class SendUploadSpeed(ServerMessage):
    """ Server code: 121 """
    """ We send this after a finished upload to let the server update the speed
    statistics for ourselves. """

    def __init__(self, speed=None):
        self.speed = speed

    def make_network_message(self):
        return self.pack_object(self.speed)


class UserPrivileged(ServerMessage):
    """ Server code: 122 """
    """ We ask the server whether a user is privileged or not. """
    """ DEPRECATED """

    def __init__(self, user=None):
        self.user = user
        self.privileged = None

    def make_network_message(self):
        return self.pack_object(self.user)

    def parse_network_message(self, message):
        pos, self.user = self.get_object(message, str, 0)
        pos, self.privileged = pos + 1, bool(message[pos])


class GivePrivileges(ServerMessage):
    """ Server code: 123 """
    """ We give (part of) our privileges, specified in days, to another
    user on the network. """

    def __init__(self, user=None, days=None):
        self.user = user
        self.days = days

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.user))
        msg.extend(self.pack_object(self.days))

        return msg


class NotifyPrivileges(ServerMessage):
    """ Server code: 124 """
    """ DEPRECATED """

    def __init__(self, token=None, user=None):
        self.token = token
        self.user = user

    def parse_network_message(self, message):
        pos, self.token = self.get_object(message, int)
        pos, self.user = self.get_object(message, str, pos)

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.token))
        msg.extend(self.pack_object(self.user))

        return msg


class AckNotifyPrivileges(ServerMessage):
    """ Server code: 125 """
    """ DEPRECATED """

    def __init__(self, token=None):
        self.token = token

    def parse_network_message(self, message):
        _pos, self.token = self.get_object(message, int)

    def make_network_message(self):
        return self.pack_object(self.token)


class BranchLevel(ServerMessage):
    """ Server code: 126 """
    """ We tell the server what our position is in our branch (xth generation)
    on the distributed network. """

    def __init__(self, value=None):
        self.value = value

    def make_network_message(self):
        return self.pack_object(self.value)


class BranchRoot(ServerMessage):
    """ Server code: 127 """
    """ We tell the server the username of the root of the branch we’re in on
    the distributed network. """

    def __init__(self, user=None):
        self.user = user

    def make_network_message(self):
        return self.pack_object(self.user)


class ChildDepth(ServerMessage):
    """ Server code: 129 """
    """ We tell the server the maximum number of generation of children we
    have on the distributed network. """

    def __init__(self, value=None):
        self.value = value

    def make_network_message(self):
        return self.pack_object(self.value)


class PrivateRoomUsers(ServerMessage):
    """ Server code: 133 """
    """ The server sends us a list of room users that we can alter
    (add operator abilities / dismember). """

    def __init__(self):
        self.room = None
        self.numusers = None
        self.users = []

    def parse_network_message(self, message):
        pos, self.room = self.get_object(message, str)
        pos, self.numusers = self.get_object(message, int, pos)

        for _ in range(self.numusers):
            pos, user = self.get_object(message, str, pos)

            self.users.append(user)


class PrivateRoomAddUser(ServerMessage):
    """ Server code: 134 """
    """ We send this to inform the server that we've added a user to a private room. """

    def __init__(self, room=None, user=None):
        self.room = room
        self.user = user

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.room))
        msg.extend(self.pack_object(self.user))

        return msg

    def parse_network_message(self, message):
        pos, self.room = self.get_object(message, str)
        pos, self.user = self.get_object(message, str, pos)


class PrivateRoomRemoveUser(PrivateRoomAddUser):
    """ Server code: 135 """
    """ We send this to inform the server that we've removed a user from a private room. """


class PrivateRoomDismember(ServerMessage):
    """ Server code: 136 """
    """ We send this to the server to remove our own membership of a private room. """

    def __init__(self, room=None):
        self.room = room

    def make_network_message(self):
        return self.pack_object(self.room)


class PrivateRoomDisown(ServerMessage):
    """ Server code: 137 """
    """ We send this to the server to stop owning a private room. """

    def __init__(self, room=None):
        self.room = room

    def make_network_message(self):
        return self.pack_object(self.room)


class PrivateRoomSomething(ServerMessage):
    """ Server code: 138 """
    """ UNKNOWN """

    def __init__(self, room=None):
        self.room = room

    def make_network_message(self):
        return self.pack_object(self.room)

    def parse_network_message(self, message):
        _pos, self.room = self.get_object(message, str)


class PrivateRoomAdded(ServerMessage):
    """ Server code: 139 """
    """ The server sends us this message when we are added to a private room. """

    def __init__(self, room=None):
        self.room = room

    def parse_network_message(self, message):
        _pos, self.room = self.get_object(message, str)


class PrivateRoomRemoved(PrivateRoomAdded):
    """ Server code: 140 """
    """ The server sends us this message when we are removed from a private room. """


class PrivateRoomToggle(ServerMessage):
    """ Server code: 141 """
    """ We send this when we want to enable or disable invitations to private rooms. """

    def __init__(self, enabled=None):
        self.enabled = None if enabled is None else int(enabled)

    def make_network_message(self):
        return bytes([self.enabled])

    def parse_network_message(self, message):
        # When this is received, we store it in the config, and disable the appropriate menu item
        self.enabled = bool(int(message[0]))


class ChangePassword(ServerMessage):
    """ Server code: 142 """
    """ We send this to the server to change our password. We receive a
    response if our password changes. """

    def __init__(self, password=None):
        self.password = password

    def make_network_message(self):
        return self.pack_object(self.password)

    def parse_network_message(self, message):
        _pos, self.password = self.get_object(message, str)


class PrivateRoomAddOperator(PrivateRoomAddUser):
    """ Server code: 143 """
    """ We send this to the server to add private room operator abilities to a user. """


class PrivateRoomRemoveOperator(PrivateRoomAddUser):
    """ Server code: 144 """
    """ We send this to the server to remove private room operator abilities from a user. """


class PrivateRoomOperatorAdded(ServerMessage):
    """ Server code: 145 """
    """ The server send us this message when we're given operator abilities
    in a private room. """

    def __init__(self, room=None):
        self.room = room

    def parse_network_message(self, message):
        _pos, self.room = self.get_object(message, str)


class PrivateRoomOperatorRemoved(ServerMessage):
    """ Server code: 146 """
    """ The server send us this message when our operator abilities are removed
    in a private room. """

    def __init__(self, room=None):
        self.room = room

    def make_network_message(self):
        return self.pack_object(self.room)

    def parse_network_message(self, message):
        _pos, self.room = self.get_object(message, str)


class PrivateRoomOwned(ServerMessage):
    """ Server code: 148 """
    """ The server sends us a list of operators in a specific room, that we can
    remove operator abilities from. """

    def __init__(self):
        self.room = None
        self.number = None
        self.operators = []

    def parse_network_message(self, message):
        pos, self.room = self.get_object(message, str)
        pos, self.number = self.get_object(message, int, pos)

        for _ in range(self.number):
            pos, user = self.get_object(message, str, pos)

            self.operators.append(user)


class MessageUsers(ServerMessage):
    """ Server code: 149 """
    """ Sends a broadcast private message to the given list of users. """

    def __init__(self, users=None, msg=None):
        self.users = users
        self.msg = msg

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(len(self.users)))

        for user in self.users:
            msg.extend(self.pack_object(user))

        msg.extend(self.pack_object(self.msg))


class JoinPublicRoom(ServerMessage):
    """ Server code: 150 """
    """ We ask the server to send us messages from all public rooms, also
    known as public chat. """

    def make_network_message(self):
        return b""


class LeavePublicRoom(ServerMessage):
    """ Server code: 151 """
    """ We ask the server to stop sending us messages from all public rooms,
    also known as public chat. """

    def make_network_message(self):
        return b""


class PublicRoomMessage(ServerMessage):
    """ Server code: 152 """
    """ The server sends this when a new message has been written in a public
    room (every single line written in every public room). """

    def __init__(self):
        self.room = None
        self.user = None
        self.msg = None

    def parse_network_message(self, message):
        pos, self.room = self.get_object(message, str)
        pos, self.user = self.get_object(message, str, pos)
        pos, self.msg = self.get_object(message, str, pos)


class RelatedSearch(ServerMessage):
    """ Server code: 153 """
    """ The server returns a list of related search terms for a search query. """
    """ DEPRECATED ? (empty list from server as of 2018) """

    def __init__(self, query=None):
        self.query = query
        self.terms = []

    def make_network_message(self):
        return self.pack_object(self.query)

    def parse_network_message(self, message):
        pos, self.query = self.get_object(message, str)
        pos, num = self.get_object(message, int, pos)

        for _ in range(num):
            pos, term = self.get_object(message, str, pos)
            pos, score = self.get_object(message, int, pos)

            self.terms.append((term, score))


class CantConnectToPeer(ServerMessage):
    """ Server code: 1001 """
    """ We send this to say we can't connect to peer after it has asked us
    to connect. We receive this if we asked peer to connect and it can't do
    this. This message means a connection can't be established either way. """

    def __init__(self, token=None, user=None):
        self.token = token
        self.user = user

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.token))
        msg.extend(self.pack_object(self.user))

        return msg

    def parse_network_message(self, message):
        _pos, self.token = self.get_object(message, int)


class CantCreateRoom(ServerMessage):
    """ Server code: 1003 """
    """ Server tells us a new room cannot be created. This message only seems
    to be sent if you try to create a room with the same name as an existing
    private room. In other cases, such as using a room name with leading or
    trailing spaces, only a private message containing an error message is sent. """

    def __init__(self):
        self.room = None

    def parse_network_message(self, message):
        _pos, self.room = self.get_object(message, str)


"""
Peer Init Messages
"""


class PeerInitMessage(SlskMessage):
    pass


class PierceFireWall(PeerInitMessage):
    """ Peer init code: 0 """
    """ This is the very first message sent by the peer that established a
    connection, if it has been asked by the other peer to do so. The token
    is taken from the ConnectToPeer server message. """

    def __init__(self, conn=None, token=None):
        self.conn = conn
        self.token = token

    def make_network_message(self):
        return self.pack_object(self.token)

    def parse_network_message(self, message):
        if message:
            # A token is not guaranteed to be sent
            _pos, self.token = self.get_object(message, int)


class PeerInit(PeerInitMessage):
    """ Peer init code: 1 """
    """ This message is sent by the peer that initiated a connection,
    not necessarily a peer that actually established it. Token apparently
    can be anything. Type is 'P' if it's anything but filetransfer,
    'F' otherwise. """

    def __init__(self, conn=None, init_user=None, target_user=None, conn_type=None, token=None):
        self.conn = conn
        self.init_user = init_user      # username of peer who initiated the message
        self.target_user = target_user  # username of peer we're connected to
        self.conn_type = conn_type
        self.token = token

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.init_user))
        msg.extend(self.pack_object(self.conn_type))
        msg.extend(self.pack_object(self.token))

        return msg

    def parse_network_message(self, message):
        pos, self.init_user = self.get_object(message, str)
        pos, self.conn_type = self.get_object(message, str, pos)

        if message[pos:]:
            # A token is not guaranteed to be sent
            pos, self.token = self.get_object(message, int, pos)

        if self.target_user is None:
            # The user we're connecting to initiated the connection. Set them as target user.
            self.target_user = self.init_user


"""
Peer Messages
"""


class PeerMessage(SlskMessage):

    def parse_file_size(self, message, pos):

        if message[pos + INT64_SIZE - 1] == 255:
            # Soulseek NS bug: >2 GiB files show up as ~16 EiB when unpacking the size
            # as uint64 (8 bytes), due to the first 4 bytes containing the size, and the
            # last 4 bytes containing garbage (a value of 4294967295 bytes, integer limit).
            # Only unpack the first 4 bytes to work around this issue.

            pos, size = self.get_object(message, int, pos)
            pos, _garbage = self.get_object(message, int, pos)

        else:
            # Everything looks fine, parse size as usual
            pos, size = self.get_object(message, int, pos, getunsignedlonglong=True)

        return pos, size


class GetSharedFileList(PeerMessage):
    """ Peer code: 4 """
    """ We send this to a peer to ask for a list of shared files. """

    def __init__(self, conn):
        self.conn = conn

    def make_network_message(self):
        return b""

    def parse_network_message(self, message):
        # Empty message
        pass


class SharedFileList(PeerMessage):
    """ Peer code: 5 """
    """ A peer responds with a list of shared files when we've sent
    a GetSharedFileList. """

    def __init__(self, conn, shares=None):
        self.conn = conn
        self.list = shares
        self.unknown = 0
        self.privatelist = []
        self.built = None

    def parse_network_message(self, message):
        try:
            message = zlib.decompress(message)
            self._parse_network_message(message)

        except Exception as error:
            log.add("Exception during parsing %(area)s: %(exception)s",
                    {'area': 'SharedFileList', 'exception': error})
            self.list = {}

    def _parse_result_list(self, message, pos=0):
        pos, ndir = self.get_object(message, int, pos)

        shares = []
        for _ in range(ndir):
            pos, directory = self.get_object(message, str, pos)
            directory = directory.replace('/', '\\')
            pos, nfiles = self.get_object(message, int, pos)

            files = []

            for _ in range(nfiles):
                pos, code = pos + 1, message[pos]
                pos, name = self.get_object(message, str, pos)
                pos, size = self.parse_file_size(message, pos)
                pos, ext = self.get_object(message, str, pos)
                pos, numattr = self.get_object(message, int, pos)

                attrs = []

                for _ in range(numattr):
                    pos, _attrnum = self.get_object(message, int, pos)
                    pos, attr = self.get_object(message, int, pos)
                    attrs.append(attr)

                files.append((code, name, size, ext, attrs))

            shares.append((directory, files))

        return pos, shares

    def _parse_network_message(self, message):
        pos, self.list = self._parse_result_list(message)

        if message[pos:]:
            pos, self.unknown = self.get_object(message, int, pos)

        if message[pos:] and config.sections["ui"]["private_shares"]:
            pos, self.privatelist = self._parse_result_list(message, pos)

    def make_network_message(self):
        # Elaborate hack to save CPU
        # Store packed message contents in self.built, and use instead of repacking it
        if self.built is not None:
            return self.built

        msg = bytearray()

        if self.list is None:
            # DB is closed
            msg.extend(self.pack_object(0))

        else:
            try:
                msg.extend(self.pack_object(len(self.list)))

            except TypeError:
                msg.extend(self.pack_object(len(list(self.list))))

            for key in self.list:
                try:
                    msg.extend(self.pack_object(key.replace('/', '\\')))
                    msg.extend(self.list[key])
                except KeyError:
                    pass

        # Unknown purpose, but official clients always send a value of 0
        msg.extend(self.pack_object(self.unknown))

        self.built = zlib.compress(msg)
        return self.built


class FileSearchRequest(PeerMessage):
    """ Peer code: 8 """
    """ We send this to the peer when we search for a file.
    Alternatively, the peer sends this to tell us it is
    searching for a file. """
    """ DEPRECATED, use UserSearch server message """

    def __init__(self, conn, requestid=None, text=None):
        self.conn = conn
        self.requestid = requestid
        self.text = text
        self.searchid = None
        self.searchterm = None

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.requestid))
        msg.extend(self.pack_object(self.text))

        return msg

    def parse_network_message(self, message):
        pos, self.searchid = self.get_object(message, int)
        pos, self.searchterm = self.get_object(message, str, pos)


class FileSearchResult(PeerMessage):
    """ Peer code: 9 """
    """ A peer sends this message when it has a file search match. The
    token/ticket is taken from original FileSearch, UserSearch or
    RoomSearch message. """

    __slots__ = ("conn", "user", "geoip", "token", "list", "privatelist", "fileindex", "freeulslots",
                 "ulspeed", "inqueue", "fifoqueue", "numresults", "pos")

    def __init__(self, conn=None, user=None, token=None, shares=None, fileindex=None, freeulslots=None,
                 ulspeed=None, inqueue=None, fifoqueue=None, numresults=None):
        self.conn = conn
        self.user = user
        self.token = token
        self.list = shares
        self.privatelist = []
        self.fileindex = fileindex
        self.freeulslots = freeulslots
        self.ulspeed = ulspeed
        self.inqueue = inqueue
        self.fifoqueue = fifoqueue
        self.numresults = numresults

    def parse_network_message(self, message):
        try:
            message = zlib.decompress(message)
            self._parse_network_message(message)
        except Exception as error:
            log.add("Exception during parsing %(area)s: %(exception)s",
                    {'area': 'FileSearchResult', 'exception': error})
            self.list = {}

    def _parse_result_list(self, message, pos):
        pos, nfiles = self.get_object(message, int, pos)

        shares = []
        for _ in range(nfiles):
            pos, code = pos + 1, message[pos]
            pos, name = self.get_object(message, str, pos)
            pos, size = self.parse_file_size(message, pos)
            pos, ext = self.get_object(message, str, pos)
            pos, numattr = self.get_object(message, int, pos)

            attrs = []
            if numattr:
                for _ in range(numattr):
                    pos, _attrnum = self.get_object(message, int, pos)
                    pos, attr = self.get_object(message, int, pos)
                    attrs.append(attr)

            shares.append((code, name.replace('/', '\\'), size, ext, attrs))

        return pos, shares

    def _parse_network_message(self, message):
        pos, self.user = self.get_object(message, str)
        pos, self.token = self.get_object(message, int, pos)

        if self.token not in SEARCH_TOKENS_ALLOWED:
            # Results are no longer accepted for this search token, stop parsing message
            return

        pos, self.list = self._parse_result_list(message, pos)

        pos, self.freeulslots = pos + 1, message[pos]
        pos, self.ulspeed = self.get_object(message, int, pos)
        pos, self.inqueue = self.get_object(message, int, pos, getunsignedlonglong=True)

        if message[pos:] and config.sections["ui"]["private_search_results"]:
            pos, self.privatelist = self._parse_result_list(message, pos)

    def pack_file_info(self, fileinfo):
        msg = bytearray()
        msg.extend(bytes([1]))
        msg.extend(self.pack_object(fileinfo[0].replace('/', '\\')))
        msg.extend(self.pack_object(fileinfo[1], unsignedlonglong=True))

        if fileinfo[2] is None or fileinfo[3] is None:
            # No metadata
            msg.extend(self.pack_object(''))
            msg.extend(self.pack_object(0))
        else:
            # FileExtension, NumAttributes
            msg.extend(self.pack_object("mp3"))
            msg.extend(self.pack_object(3))

            # Length
            msg.extend(self.pack_object(0))
            msg.extend(self.pack_object(fileinfo[2][0] or 0))

            # Duration
            msg.extend(self.pack_object(1))
            msg.extend(self.pack_object(fileinfo[3] or 0))

            # VBR
            msg.extend(self.pack_object(2))
            msg.extend(self.pack_object(fileinfo[2][1] or 0))

        return msg

    def make_network_message(self):
        msg_list = bytearray()
        final_num_results = 0

        for index in islice(self.list, self.numresults):
            try:
                fileinfo = self.fileindex[repr(index)]
                final_num_results += 1

            except Exception:
                log.add(
                    _("Your shares database is corrupted. Please rescan your shares and report "
                      "any potential scanning issues to the developers.")
                )
                break

            msg_list.extend(self.pack_file_info(fileinfo))

        msg = bytearray()
        msg.extend(self.pack_object(self.user))
        msg.extend(self.pack_object(self.token))
        msg.extend(self.pack_object(final_num_results))

        # We generate the result list early, so we don't send an incorrect result count
        # if something goes wrong when reading the file index database
        msg.extend(msg_list)

        msg.extend(bytes([self.freeulslots]))
        msg.extend(self.pack_object(self.ulspeed))
        msg.extend(self.pack_object(self.inqueue, unsignedlonglong=True))

        return zlib.compress(msg)


class UserInfoRequest(PeerMessage):
    """ Peer code: 15 """
    """ We ask the other peer to send us their user information, picture
    and all."""

    def __init__(self, conn):
        self.conn = conn

    def make_network_message(self):
        return b""

    def parse_network_message(self, message):
        # Empty message
        pass


class UserInfoReply(PeerMessage):
    """ Peer code: 16 """
    """ A peer responds with this when we've sent a UserInfoRequest. """

    def __init__(self, conn, descr=None, pic=None, totalupl=None, queuesize=None, slotsavail=None, uploadallowed=None):
        self.conn = conn
        self.descr = descr
        self.pic = pic
        self.totalupl = totalupl
        self.queuesize = queuesize
        self.slotsavail = slotsavail
        self.uploadallowed = uploadallowed
        self.has_pic = None

    def parse_network_message(self, message):
        pos, self.descr = self.get_object(message, str)
        pos, self.has_pic = pos + 1, message[pos]

        if self.has_pic:
            pos, self.pic = self.get_object(message, bytes, pos)

        pos, self.totalupl = self.get_object(message, int, pos)
        pos, self.queuesize = self.get_object(message, int, pos)
        pos, self.slotsavail = pos + 1, message[pos]

        # To prevent errors, ensure that >= 4 bytes are left. Museek+ incorrectly sends
        # slotsavail as an integer, resulting in 3 bytes of garbage here.
        if len(message[pos:]) >= 4:
            pos, self.uploadallowed = self.get_object(message, int, pos)

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.descr))

        if self.pic is not None:
            msg.extend(bytes([1]))
            msg.extend(self.pack_object(self.pic))
        else:
            msg.extend(bytes([0]))

        msg.extend(self.pack_object(self.totalupl))
        msg.extend(self.pack_object(self.queuesize))
        msg.extend(bytes([self.slotsavail]))
        msg.extend(self.pack_object(self.uploadallowed))

        return msg


class PMessageUser(PeerMessage):
    """ Peer code: 22 """
    """ Chat phrase sent to someone or received by us in private.
    This is a Nicotine+ extension to the Soulseek protocol. """
    """ DEPRECATED """

    def __init__(self, conn=None, user=None, msg=None):
        self.conn = conn
        self.user = user
        self.msg = msg
        self.msgid = None
        self.timestamp = None

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(0))
        msg.extend(self.pack_object(0))
        msg.extend(self.pack_object(self.user))
        msg.extend(self.pack_object(self.msg))

        return msg

    def parse_network_message(self, message):
        pos, self.msgid = self.get_object(message, int)
        pos, self.timestamp = self.get_object(message, int, pos)
        pos, self.user = self.get_object(message, str, pos)
        pos, self.msg = self.get_object(message, str, pos)


class FolderContentsRequest(PeerMessage):
    """ Peer code: 36 """
    """ We ask the peer to send us the contents of a single folder. """

    def __init__(self, conn, directory=None):
        self.conn = conn
        self.dir = directory
        self.something = None

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(1))
        msg.extend(self.pack_object(self.dir, latin1=True))

        return msg

    def parse_network_message(self, message):
        pos, self.something = self.get_object(message, int)
        pos, self.dir = self.get_object(message, str, pos)


class FolderContentsResponse(PeerMessage):
    """ Peer code: 37 """
    """ A peer responds with the contents of a particular folder
    (with all subfolders) when we've sent a FolderContentsRequest. """

    def __init__(self, conn, directory=None, shares=None):
        self.conn = conn
        self.dir = directory
        self.list = shares

    def parse_network_message(self, message):
        try:
            message = zlib.decompress(message)
            self._parse_network_message(message)
        except Exception as error:
            log.add("Exception during parsing %(area)s: %(exception)s",
                    {'area': 'FolderContentsResponse', 'exception': error})
            self.list = {}

    def _parse_network_message(self, message):
        shares = {}
        pos, nfolders = self.get_object(message, int)

        for _ in range(nfolders):
            pos, folder = self.get_object(message, str, pos)

            shares[folder] = {}

            pos, ndir = self.get_object(message, int, pos)

            for _ in range(ndir):
                pos, directory = self.get_object(message, str, pos)
                directory = directory.replace('/', '\\')
                pos, nfiles = self.get_object(message, int, pos)

                shares[folder][directory] = []

                for _ in range(nfiles):
                    pos, code = pos + 1, message[pos]
                    pos, name = self.get_object(message, str, pos)
                    pos, size = self.get_object(message, int, pos, getunsignedlonglong=True)
                    pos, ext = self.get_object(message, str, pos)
                    pos, numattr = self.get_object(message, int, pos)

                    attrs = []

                    for _ in range(numattr):
                        pos, _attrnum = self.get_object(message, int, pos)
                        pos, attr = self.get_object(message, int, pos)
                        attrs.append(attr)

                    shares[folder][directory].append((code, name, size, ext, attrs))

        self.list = shares

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(1))
        msg.extend(self.pack_object(self.dir))
        msg.extend(self.pack_object(1))
        msg.extend(self.pack_object(self.dir))

        if self.list is not None:
            # We already saved the folder contents as a bytearray when scanning our shares
            msg.extend(self.list)
        else:
            # No folder contents
            msg.extend(self.pack_object(0))

        return zlib.compress(msg)


class TransferRequest(PeerMessage):
    """ Peer code: 40 """
    """ This message is sent by a peer once they are ready to start uploading a file.
    A TransferResponse message is expected from the recipient, either allowing or
    rejecting the upload attempt.

    This message was formely used to send a download request (direction 0) as well,
    but Nicotine+, Museek+ and the official clients use the QueueUpload message for
    this purpose today. """

    def __init__(self, conn, direction=None, req=None, file=None, filesize=None, realfile=None, legacy_client=False):
        self.conn = conn
        self.direction = direction
        self.req = req
        self.file = file  # virtual file
        self.realfile = realfile
        self.filesize = filesize
        self.legacy_client = legacy_client

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.direction))
        msg.extend(self.pack_object(self.req))
        msg.extend(self.pack_object(self.file, latin1=self.legacy_client))

        if self.filesize is not None and self.direction == 1:
            msg.extend(self.pack_object(self.filesize, unsignedlonglong=True))

        return msg

    def parse_network_message(self, message):
        pos, self.direction = self.get_object(message, int)
        pos, self.req = self.get_object(message, int, pos)
        pos, self.file = self.get_object(message, str, pos)

        if self.direction == 1:
            pos, self.filesize = self.get_object(message, int, pos, getunsignedlonglong=True)


class TransferResponse(PeerMessage):
    """ Peer code: 41 """
    """ Response to TransferRequest - either we (or the other peer) agrees,
    or tells the reason for rejecting the file transfer. """

    def __init__(self, conn, allowed=None, reason=None, req=None, filesize=None):
        self.conn = conn
        self.allowed = allowed
        self.req = req
        self.reason = reason
        self.filesize = filesize

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.req))
        msg.extend(bytes([self.allowed]))

        if self.reason is not None:
            msg.extend(self.pack_object(self.reason))

        if self.filesize is not None:
            msg.extend(self.pack_object(self.filesize, unsignedlonglong=True))

        return msg

    def parse_network_message(self, message):
        pos, self.req = self.get_object(message, int)
        pos, self.allowed = pos + 1, message[pos]

        if message[pos:]:
            if self.allowed:
                pos, self.filesize = self.get_object(message, int, pos, getunsignedlonglong=True)
            else:
                pos, self.reason = self.get_object(message, str, pos)


class PlaceholdUpload(PeerMessage):
    """ Peer code: 42 """
    """ DEPRECATED """

    def __init__(self, conn, file=None, legacy_client=False):
        self.conn = conn
        self.file = file
        self.legacy_client = legacy_client

    def make_network_message(self):
        return self.pack_object(self.file, latin1=self.legacy_client)

    def parse_network_message(self, message):
        _pos, self.file = self.get_object(message, str)


class QueueUpload(PlaceholdUpload):
    """ Peer code: 43 """
    """ This message is used to tell a peer that an upload should be queued on their end.
    Once the recipient is ready to transfer the requested file, they will send an upload
    request."""


class PlaceInQueue(PeerMessage):
    """ Peer code: 44 """
    """ The peer replies with the upload queue placement of the requested file. """

    def __init__(self, conn, filename=None, place=None):
        self.conn = conn
        self.filename = filename
        self.place = place

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.filename))
        msg.extend(self.pack_object(self.place))

        return msg

    def parse_network_message(self, message):
        pos, self.filename = self.get_object(message, str)
        pos, self.place = self.get_object(message, int, pos)


class UploadFailed(PlaceholdUpload):
    """ Peer code: 46 """
    """ This message is sent whenever a file connection of an active upload
    closes. Soulseek NS clients can also send this message when a file can
    not be read. The recipient either re-queues the upload (download on their
    end), or ignores the message if the transfer finished. """


class UploadDenied(PeerMessage):
    """ Peer code: 50 """
    """ This message is sent to reject QueueUpload attempts and previously queued
    files. The reason for rejection will appear in the transfer list of the recipient. """

    def __init__(self, conn, file=None, reason=None):
        self.conn = conn
        self.file = file
        self.reason = reason

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.file))
        msg.extend(self.pack_object(self.reason))

        return msg

    def parse_network_message(self, message):
        pos, self.file = self.get_object(message, str)
        pos, self.reason = self.get_object(message, str, pos)


class PlaceInQueueRequest(PlaceholdUpload):
    """ Peer code: 51 """
    """ This message is sent when asking for the upload queue placement of a file. """


class UploadQueueNotification(PeerMessage):
    """ Peer code: 52 """
    """ DEPRECATED """

    def __init__(self, conn):
        self.conn = conn

    def make_network_message(self):
        return b""

    def parse_network_message(self, _message):
        return b""


class UnknownPeerMessage(PeerMessage):
    """ Peer code: 12547 """
    """ UNKNOWN """

    def __init__(self, conn):
        self.conn = conn

    def parse_network_message(self, message):
        # Empty message
        pass


"""
File Messages
"""


class FileMessage(SlskMessage):
    pass


class FileRequest(FileMessage):
    """ We sent this to a peer via a 'F' connection to tell them that we want to
    start uploading a file. The token is the same as the one previously included
    in the TransferRequest message. """

    def __init__(self, conn, req=None):
        self.conn = conn
        self.req = req

    def make_network_message(self):
        msg = self.pack_object(self.req)
        return msg

    def parse_network_message(self, message):
        _pos, self.req = self.get_object(message, int)


class FileOffset(FileMessage):
    """ We send this to the uploading peer at the beginning of a 'F' connection,
    to tell them how many bytes of the file we've previously downloaded. If none,
    the offset is 0. """

    def __init__(self, conn, filesize=None, offset=None):
        self.conn = conn
        self.filesize = filesize
        self.offset = offset

    def make_network_message(self):
        msg = self.pack_object(self.offset, unsignedlonglong=True)
        return msg

    def parse_network_message(self, message):
        _pos, self.offset = self.get_object(message, int, getunsignedlonglong=True)


"""
Distributed Messages
"""


class DistribMessage(SlskMessage):
    pass


class DistribRequest(InternalMessage):
    """ Used to identify a connection attempt to a distributed parent. """


class DistribAlive(DistribMessage):
    """ Distrib code: 0 """

    def __init__(self, conn):
        self.conn = conn

    def make_network_message(self):
        return b""

    def parse_network_message(self, message):
        # Empty message
        pass


class DistribSearch(DistribMessage):
    """ Distrib code: 3 """
    """ Search request that arrives through the distributed network.
    We transmit the search request to our child peers. """

    __slots__ = ("unknown", "conn", "user", "searchid", "searchterm")

    def __init__(self, conn):
        self.conn = conn
        self.unknown = None
        self.user = None
        self.searchid = None
        self.searchterm = None

    def parse_network_message(self, message):
        try:
            self._parse_network_message(message)

        except Exception as error:
            log.add("Exception during parsing %(area)s: %(exception)s",
                    {'area': 'DistribSearch', 'exception': error})

    def _parse_network_message(self, message):
        pos, self.unknown = self.get_object(message, int)
        pos, self.user = self.get_object(message, str, pos)
        pos, self.searchid = self.get_object(message, int, pos)
        pos, self.searchterm = self.get_object(message, str, pos)


class DistribBranchLevel(DistribMessage):
    """ Distrib code: 4 """

    def __init__(self, conn, value=None):
        self.conn = conn
        self.value = value

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.value, signedint=True))

        return msg

    def parse_network_message(self, message):
        _pos, self.value = self.get_object(message, int, getsignedint=True)


class DistribBranchRoot(DistribMessage):
    """ Distrib code: 5 """

    def __init__(self, conn, user=None):
        self.conn = conn
        self.user = user

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.user))

        return msg

    def parse_network_message(self, message):
        _pos, self.user = self.get_object(message, str)


class DistribChildDepth(DistribMessage):
    """ Distrib code: 7 """

    def __init__(self, conn, value=None):
        self.conn = conn
        self.value = value

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_object(self.value))

        return msg

    def parse_network_message(self, message):
        _pos, self.value = self.get_object(message, int)


class DistribEmbeddedMessage(DistribMessage):
    """ Distrib code: 93 """
    """ A branch root sends us an embedded distributed message. The only type
    of distributed message sent at present is DistribSearch (distributed code 3).
    We unpack the distributed message and distribute it to our child peers. """

    __slots__ = ("conn", "distrib_code", "distrib_message")

    def __init__(self, conn, distrib_code=None, distrib_message=None):
        self.conn = conn
        self.distrib_code = distrib_code
        self.distrib_message = distrib_message

    def make_network_message(self):
        msg = bytearray()
        msg.extend(bytes([self.distrib_code]))
        msg.extend(self.distrib_message)

        return msg

    def parse_network_message(self, message):
        self.distrib_code = message[3]
        self.distrib_message = message[4:]
