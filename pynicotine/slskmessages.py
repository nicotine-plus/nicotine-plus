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

import hashlib
import os
import socket
import struct
import zlib
from gettext import gettext as _
from itertools import count
from typing import Union

from pynicotine.logfacility import log
from pynicotine.utils import debug

""" This module contains message classes, that networking and UI thread
exchange. Basically there are three types of messages: internal messages,
server messages and p2p messages (between clients)."""

counter = count(100)


def newId():
    global counter
    Id = next(counter)
    return Id

# Python objects cannot be used as a source to determine the network object,
# since diff. OS/Arch will have diff. ranges for Integers, Longs, etc.
#
# By default they are all unsigned unless noted otherwise


def _str(arg: Union[bytes, str]) -> str:
    """
    Until we figure out the best way to convert between protocol messages, which
    are in bytes, and strings, use this function explicitly
    """
    if isinstance(arg, bytes):
        return arg.decode('utf-8')
    elif isinstance(arg, str):
        return arg
    return arg


class NetworkBaseType:
    """Base class for other network types."""
    def __init__(self, value):
        self.value = value


class NetworkShortIntType(NetworkBaseType):
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


class ToBeEncoded:
    """Holds text and the desired eventual encoding"""
    def __init__(self, uni, encoding):
        if not isinstance(uni, str):
            raise ValueError("ZOMG, you really don't know what you're doing! %s is NOT unicode, its a %s: %s" % (uni, type(uni), repr(uni)))
        self.str = uni
        self.encoding = encoding
        self.cached = None

    def getbytes(self):
        if self.cached:
            return self.cached
        self.cached = self.str.encode(self.encoding, "replace")
        # print "The bytes of %s are %s" % (self.unicode, repr(self.cached))
        return self.cached

    def dont(self):
        print("Dont do that")
    bytes = property(getbytes, dont)

    def __getitem__(self, key):
        return self.str[key]

    def __str__(self):
        return "%s" % (self.getbytes(),)

    def __repr__(self):
        return "ToBeEncoded(%s, %s)" % (repr(self.getbytes()), self.encoding)


class JustDecoded:
    """Holds text, the original bytes and its supposed encoding"""
    def __init__(self, bytes, encoding):
        if not isinstance(bytes, str):
            raise ValueError("ZOMG, you really don't know what you're doing! %s is NOT string, its a %s: %s" % (bytes, type(bytes), repr(bytes)))
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
        if not isinstance(uni, str):
            print("ZOMG, you really don't know what you're doing! %s is NOT unicode, its a %s: %s" % (uni, type(uni), repr(bytes)))
            raise Exception
        self.cached = uni
    str = property(getunicode, setunicode)

    def __getitem__(self, key):
        return self.str[key]

    def __str__(self):
        return "%s" % (self.getbytes(),)

    def __repr__(self):
        return "ToBeEncoded(%s, %s)" % (repr(self.getbytes()), self.encoding)


class InternalMessage:
    pass


class ConnectToServer(InternalMessage):
    pass


class Conn(InternalMessage):
    def __init__(self, conn=None, addr=None, init=None):
        self.conn = conn
        self.addr = addr
        self.init = init

    def __repr__(self):
        return f"{type(self).__name__}: {self.conn} {self.addr} {self.init}"


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
    def __init__(self, connobj=None, err=None):
        self.connobj = connobj
        self.err = err


class IncPort(InternalMessage):
    """ Send by networking thread to tell UI thread the port number client
    listens on."""
    def __init__(self, port=None):
        self.port = port


class PeerTransfer(InternalMessage):
    """ Used to indicate progress of long transfers. """
    def __init__(self, conn=None, total=None, bytes=None, msg=None):
        self.conn = conn
        self.bytes = bytes
        self.total = total
        self.msg = _str(msg)


class DownloadFile(InternalMessage):
    """ Sent by networking thread to indicate file transfer progress.
    Sent by UI to pass the file object to write and offset to resume download
    from. """
    def __init__(self, conn=None, offset=None, file=None, filesize=None):
        self.conn = conn
        self.offset = offset
        self.file = _str(file)
        self.filesize = filesize


class UploadFile(InternalMessage):
    def __init__(self, conn=None, file=None, size=None, sentbytes=0, offset=None):
        self.conn = conn
        self.file = _str(file)
        self.size = size
        self.sentbytes = sentbytes
        self.offset = offset


class FileError(InternalMessage):
    """ Sent by networking thread to indicate that a file error occurred during
    filetransfer. """
    def __init__(self, conn=None, file=None, strerror=None):
        self.conn = conn
        self.file = _str(file)
        self.strerror = _str(strerror)


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
        self.msg = _str(msg)


class InternalData(InternalMessage):
    def __init__(self, msg):
        self.msg = _str(msg)


class DebugMessage(InternalMessage):
    def __init__(self, msg, debugLevel=None):
        ''' debugLevel Options
        0/None - Normal messages and (Human-Readable) Errors
        1 - Warnings & Tracebacks
        2 - Search Results
        3 - Peer Connections
        4 - Message Contents
        5 - Transfers
        6 - Connection, Bandwidth and Usage Statistics
        '''
        self.msg = _str(msg)
        self.debugLevel = debugLevel


class SlskMessage:
    """ This is a parent class for all protocol messages. """
    def getObject(self, message, type, start=0, getintasshort=0, getsignedint=0, printerror=True):
        """ Returns object of specified type, extracted from message (which is
        a binary array). start is an offset."""
        intsize = struct.calcsize("<I")
        try:
            if type is int:
                if getintasshort:
                    return intsize + start, struct.unpack("<H", message[start:start + struct.calcsize("<H")])[0]
                elif getsignedint:
                    return intsize + start, struct.unpack("<i", message[start:start + intsize])[0]
                else:
                    return intsize + start, struct.unpack("<I", message[start:start + intsize])[0]

            elif type is bytes:
                length = struct.unpack("<I", message[start:start + intsize])[0]
                string = message[start + intsize:start + length + intsize].decode('utf-8', errors='replace')
                return length + intsize + start, string
            elif type is NetworkIntType:
                return intsize + start, struct.unpack("<I", message[start:start + intsize])[0]
            elif type is NetworkSignedIntType:
                return intsize + start, struct.unpack("<i", message[start:start + intsize])[0]
            elif type is NetworkLongLongType:
                return struct.calcsize("<Q") + start, struct.unpack("<Q", message[start:start + struct.calcsize("<Q")])[0]
            else:
                return start, None
        except struct.error as error:
            if printerror:
                log.addwarning("%s %s trying to unpack %s at '%s' at %s/%s" % (self.__class__, error, type, message[start:].__repr__(), start, len(message)))
            raise struct.error(error)
            # return start, None

    def packObject(self, object):
        """ Returns object (integer, long or string packed into a
        binary array."""
        if type(object) is int:
            if object.bit_length() <= 32:
                return struct.pack("<i", object)
            else:
                return struct.pack("<Q", object)
        elif type(object) is bytes:
            return struct.pack("<i", len(object)) + object
        elif type(object) is ToBeEncoded:
            # The server seems to cut off strings at \x00 regardless of the length
            return struct.pack("<i", len(object.bytes)) + object.bytes
        elif type(object) is str:
            encoded = object.encode("utf-8", 'replace')
            return struct.pack("<i", len(encoded)) + encoded
        elif type(object) is NetworkIntType:
            return struct.pack("<I", object.value)
        elif type(object) is NetworkSignedIntType:
            return struct.pack("<i", object.value)
        elif type(object) is NetworkLongLongType:
            return struct.pack("<Q", object.value)
        log.addwarning(_("Warning: unknown object type %s") % type(object) + " " + "in message %(type)s" % {'type': self.__class__})
        return b""

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
            # log.add('Decoding %s with LongLong...' % messagename)
            self._parseNetworkMessage(message, NetworkLongLongType)
        except struct.error as e:
            try:
                # log.add('Decoding %s with Int...' % messagename)
                self._parseNetworkMessage(message, NetworkIntType)
            except struct.error as f:
                lines = []
                lines.append(_("Exception during parsing %(area)s: %(exception)s") % {'area': 'first ' + messagename, 'exception': e})
                lines.append(_("Exception during parsing %(area)s: %(exception)s") % {'area': 'second ' + messagename, 'exception': f})
                lines.append(_("Offending package: %(bytes)s") % {'bytes': repr(message[:1000])})
                log.addwarning("\n".join(lines))
                return False
        # log.add('Successfully decoded %s' % messagename)
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
        debug(type(self).__name__, self.__dict__, message.__repr__())


class ServerMessage(SlskMessage):
    pass


class PeerMessage(SlskMessage):
    pass


class DistribMessage(SlskMessage):
    pass


class Login(ServerMessage):
    """ We sent this to the server right after the connection has been
    established. Server responds with the greeting message. """

    def __init__(self, username=None, passwd=None, version=None):
        # TODO: use _str(). also needs to be changed downstream, so defer change for now.
        self.username = username
        self.passwd = passwd
        self.version = version
        self.ip = None

    def __repr__(self):
        return f"Login({self.username}, {self.version}, {self.ip})"

    def makeNetworkMessage(self):
        payload = self.username + self.passwd
        md5hash = hashlib.md5(payload.encode()).hexdigest()
        message = self.packObject(self.username) + self.packObject(self.passwd) + self.packObject(self.version) + self.packObject(md5hash) + self.packObject(17)
        return message

    def parseNetworkMessage(self, message):
        pos, self.success = 1, message[0]
        if not self.success:
            pos, self.reason = self.getObject(message, bytes, pos)

        else:
            pos, self.banner = self.getObject(message, bytes, pos)
        if len(message[pos:]) > 0:
            try:
                import socket
                pos, self.ip = pos + 4, socket.inet_ntoa(message[pos:pos + 4][::-1])
                # Unknown number
            except Exception as error:
                log.addwarning("Error unpacking IP address: %s" % (error,))
            try:
                # MD5 hexdigest of the password you sent
                if len(message[pos:]) > 0:
                    pos, self.checksum = self.getObject(message, bytes, pos)
                # print self.checksum
            except Exception:
                # Not an official client on the official server
                pass


class ChangePassword(ServerMessage):
    """ We sent this to the server to change our password
    We receive a response if our password changes. """

    def __init__(self, password=None):
        self.password = _str(password)

    def makeNetworkMessage(self):
        return self.packObject(self.password)

    def parseNetworkMessage(self, message):
        pos, self.password = self.getObject(message, bytes)


class SetWaitPort(ServerMessage):
    """ Send this to server to indicate port number that we listen on."""
    def __init__(self, port=None):
        self.port = port

    def __repr__(self):
        return f"SetWaitPort({self.port})"

    def makeNetworkMessage(self):
        return self.packObject(NetworkIntType(self.port))


class GetPeerAddress(ServerMessage):
    """ Used to find out a peer's (ip, port) address."""
    def __init__(self, user=None):
        self.user = _str(user)

    def makeNetworkMessage(self):
        return self.packObject(self.user)

    def parseNetworkMessage(self, message):
        pos, self.user = self.getObject(message, bytes)
        import socket
        pos, self.ip = pos + 4, socket.inet_ntoa(message[pos:pos + 4][::-1])
        pos, self.port = self.getObject(message, int, pos, 1)


class AddUser(ServerMessage):
    """ Used to be kept updated about a user's status."""
    def __init__(self, user=None):
        self.user = _str(user)
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
        pos, self.user = self.getObject(message, bytes)
        pos, self.userexists = pos + 1, message[pos]
        if len(message[pos:]) > 0:
            pos, self.status = self.getObject(message, int, pos)
            pos, self.avgspeed = self.getObject(message, int, pos)
            pos, self.downloadnum = self.getObject(message, int, pos, getsignedint=1)

            pos, self.files = self.getObject(message, int, pos)
            pos, self.dirs = self.getObject(message, int, pos)
            if len(message[pos:]) > 0:
                pos, self.country = self.getObject(message, bytes, pos)


class Unknown6(ServerMessage):
    """ Message 6 """
    def __init__(self, user=None):
        self.user = _str(user)

    def makeNetworkMessage(self):
        return self.packObject(self.user)

    def parseNetworkMessage(self, message):
        self.debug()
        pass


class RemoveUser(ServerMessage):
    """ Used when we no longer want to be kept updated about a user's status."""
    def __init__(self, user=None):
        self.user = _str(user)

    def makeNetworkMessage(self):
        return self.packObject(self.user)


class GetUserStatus(ServerMessage):
    """ Server tells us if a user has gone away or has returned"""
    def __init__(self, user=None):
        self.user = _str(user)
        self.privileged = None

    def makeNetworkMessage(self):
        return self.packObject(self.user)

    def parseNetworkMessage(self, message):
        pos, self.user = self.getObject(message, bytes)
        pos, self.status = self.getObject(message, int, pos)
        # Exception handler is for Soulfind compatibility
        try:
            pos, self.privileged = pos + 1, message[pos]
        except Exception:
            pass


class SetStatus(ServerMessage):
    """ We send our new status to the server """
    def __init__(self, status=None):
        self.status = _str(status)

    def makeNetworkMessage(self):
        return self.packObject(self.status)


class NotifyPrivileges(ServerMessage):
    """ Server tells us something about privileges"""
    def __init__(self, token=None, user=None):
        self.token = token
        self.user = _str(user)

    def parseNetworkMessage(self, message):
        pos, self.token = self.getObject(message, int)
        pos, self.user = self.getObject(message, bytes, pos)

    def makeNetworkMessage(self):
        return self.packObject(self.token) + self.packObject(self.user)


class AckNotifyPrivileges(ServerMessage):
    def __init__(self, token=None):
        self.token = token

    def parseNetworkMessage(self, message):
        pos, self.token = self.getObject(message, int)

    def makeNetworkMessage(self):
        return self.packObject(NetworkIntType(self.token))


class JoinPublicRoom(ServerMessage):
    """We want to join the Public Chat"""
    def __init__(self, unknown=0):
        self.unknown = unknown

    def makeNetworkMessage(self):
        return self.packObject(NetworkIntType(self.unknown))


class LeavePublicRoom(ServerMessage):
    """We want to leave the Public Chat"""
    def __init__(self, unknown=0):
        self.unknown = unknown

    def makeNetworkMessage(self):
        return self.packObject(NetworkIntType(self.unknown))


class PublicRoomMessage(ServerMessage):
    """The server sends us messages from random chatrooms"""
    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos, self.user = self.getObject(message, bytes, pos)
        pos, self.msg = self.getObject(message, bytes, pos)


class SayChatroom(ServerMessage):
    """ Either we want to say something in the chatroom, or someone did."""
    def __init__(self, room=None, msg=None):
        self.room = _str(room)
        self.msg = _str(msg)

    def makeNetworkMessage(self):
        return self.packObject(self.room) + self.packObject(self.msg)

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos, self.user = self.getObject(message, bytes, pos)
        pos, self.msg = self.getObject(message, bytes, pos)


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
    def __init__(self, room=None, private=None):
        self.room = _str(room)
        self.private = private
        self.owner = None
        self.operators = []

    def makeNetworkMessage(self):
        if self.private is not None:
            return self.packObject(self.room) + self.packObject(self.private)
        return self.packObject(self.room)

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos1 = pos
        pos, self.users = self.getUsers(message[pos:])
        pos = pos1 + pos

        if len(message[pos:]) > 0:
            self.private = True
            pos, self.owner = self.getObject(message, bytes, pos)
        if len(message[pos:]) > 0 and self.private:
            pos, numops = self.getObject(message, int, pos)
            for i in range(numops):
                pos, operator = self.getObject(message, bytes, pos)
                self.operators.append(operator)

    def getUsers(self, message):
        pos, numusers = self.getObject(message, int)
        users = []
        for i in range(numusers):
            pos, username = self.getObject(message, bytes, pos)
            users.append([username, None, None, None, None, None, None, None, None])
        pos, statuslen = self.getObject(message, int, pos)
        for i in range(statuslen):
            pos, users[i][1] = self.getObject(message, int, pos)
        pos, statslen = self.getObject(message, int, pos)
        for i in range(statslen):
            pos, users[i][2] = self.getObject(message, int, pos, getsignedint=1)
            pos, users[i][3] = self.getObject(message, int, pos)
            pos, users[i][4] = self.getObject(message, int, pos)
            pos, users[i][5] = self.getObject(message, int, pos)
            pos, users[i][6] = self.getObject(message, int, pos)
        pos, slotslen = self.getObject(message, int, pos)
        for i in range(slotslen):
            pos, users[i][7] = self.getObject(message, int, pos)
        if len(message[pos:]) > 0:
            pos, countrylen = self.getObject(message, int, pos)
            for i in range(countrylen):
                pos, users[i][8] = self.getObject(message, bytes, pos)

        usersdict = {}
        for i in users:
            usersdict[i[0]] = UserData(i[1:])

        return pos, usersdict


class PrivateRoomUsers(ServerMessage):
    """ We get this when we've created a private room."""
    def __init__(self, room=None, numusers=None, users=None):
        self.room = _str(room)
        self.numusers = numusers
        self.users = users

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos, self.numusers = self.getObject(message, int, pos)
        self.users = []
        for i in range(self.numusers):
            pos, user = self.getObject(message, bytes, pos)
            self.users.append(user)


class PrivateRoomOwned(ServerMessage):
    """ We get this when we've created a private room."""
    def __init__(self, room=None, number=None):
        self.room = _str(room)
        self.number = number

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos, self.number = self.getObject(message, int, pos)
        self.operators = []
        for i in range(self.number):
            pos, user = self.getObject(message, bytes, pos)
            self.operators.append(user)


class PrivateRoomAddUser(ServerMessage):
    """ We get / receive this when we add a user to a private room."""
    def __init__(self, room=None, user=None):
        self.room = _str(room)
        self.user = _str(user)

    def makeNetworkMessage(self):
        return self.packObject(self.room) + self.packObject(self.user)

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos, self.user = self.getObject(message, bytes, pos)


class PrivateRoomDismember(ServerMessage):
    """ We do this to remove our own membership of a private room."""
    def __init__(self, room=None):
        self.room = _str(room)

    def makeNetworkMessage(self):
        return self.packObject(self.room)

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)


class PrivateRoomDisown(ServerMessage):
    """ We do this to stop owning a private room."""
    def __init__(self, room=None):
        self.room = _str(room)

    def makeNetworkMessage(self):
        return self.packObject(self.room)

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)


class PrivateRoomSomething(ServerMessage):
    """Unknown"""
    def __init__(self, room=None):
        self.room = _str(room)

    def makeNetworkMessage(self):
        return self.packObject(self.room)

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        self.debug()


class PrivateRoomRemoveUser(ServerMessage):
    """ We get this when we've removed a user from a private room."""
    def __init__(self, room=None, user=None):
        self.room = _str(room)
        self.user = _str(user)

    def makeNetworkMessage(self):
        return self.packObject(self.room) + self.packObject(self.user)

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos, self.user = self.getObject(message, bytes, pos)


class PrivateRoomAdded(ServerMessage):
    """ We are sent this when we are added to a private room."""
    def __init__(self, room=None):
        self.room = _str(room)

    def makeNetworkMessage(self):
        return self.packObject(self.room)

    def parseNetworkMessage(self, message):
        self.room = self.getObject(message, bytes)[1]


class PrivateRoomRemoved(ServerMessage):
    """ We are sent this when we are removed from a private room."""
    def __init__(self, room=None):
        self.room = _str(room)

    def makeNetworkMessage(self):
        return self.packObject(self.room)

    def parseNetworkMessage(self, message):
        self.room = self.getObject(message, bytes)[1]


class PrivateRoomToggle(ServerMessage):
    """ We send this when we want to enable or disable invitations to private rooms"""
    def __init__(self, enabled=None):
        self.enabled = None if enabled is None else int(enabled)

    def makeNetworkMessage(self):
        return bytes((self.enabled,))

    def parseNetworkMessage(self, message):
        # When this is received, we store it in the config, and disable the appropriate menu item
        pos, self.enabled = 1, bool(int(message[0]))  # noqa: F841


class PrivateRoomAddOperator(ServerMessage):
    """ We send this to add private room operator abilities to a user"""
    def __init__(self, room=None, user=None):
        self.room = _str(room)
        self.user = _str(user)

    def makeNetworkMessage(self):
        return self.packObject(self.room) + self.packObject(self.user)

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos, self.user = self.getObject(message, bytes, pos)


class PrivateRoomRemoveOperator(ServerMessage):
    """ We send this to remove privateroom operator abilities from a user"""
    def __init__(self, room=None, user=None):
        self.room = _str(room)
        self.user = _str(user)

    def makeNetworkMessage(self):
        return self.packObject(self.room) + self.packObject(self.user)

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos, self.user = self.getObject(message, bytes, pos)


class PrivateRoomOperatorAdded(ServerMessage):
    """ We receive this when given privateroom operator abilities"""
    def __init__(self, room=None):
        self.room = _str(room)

    def makeNetworkMessage(self):
        return self.packObject(self.room)

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)


class PrivateRoomOperatorRemoved(ServerMessage):
    """ We receive this when privateroom operator abilities are removed"""
    def __init__(self, room=None):
        self.room = _str(room)

    def makeNetworkMessage(self):
        return self.packObject(self.room)

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        # pos, self.username = self.getObject(message, types.StringType, pos)


class LeaveRoom(ServerMessage):
    """ We send this when we want to leave a room."""
    def __init__(self, room=None):
        self.room = _str(room)

    def makeNetworkMessage(self):
        return self.packObject(self.room)

    def parseNetworkMessage(self, message):
        self.room = self.getObject(message, bytes)[1]


class UserJoinedRoom(ServerMessage):
    """ Server tells us someone has just joined the room."""
    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos, self.username = self.getObject(message, bytes, pos)
        i = [None, None, None, None, None, None, None, None]
        pos, i[0] = self.getObject(message, int, pos)
        pos, i[1] = self.getObject(message, int, pos, getsignedint=1)
        for j in range(2, 7):
            pos, i[j] = (self.getObject(message, int, pos))
        if len(message[pos:]) > 0:
            pos, i[7] = self.getObject(message, bytes, pos)
        self.userdata = UserData(i)


class UserLeftRoom(ServerMessage):
    """ Server tells us someone has just left the room."""
    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos, self.username = self.getObject(message, bytes, pos)


class RoomTickerState(ServerMessage):
    """ Message 113 """
    def __init__(self):
        self.room = None
        self.user = None
        self.msgs = {}

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos, n = self.getObject(message, int, pos)
        for i in range(n):
            pos, user = self.getObject(message, bytes, pos)
            pos, msg = self.getObject(message, bytes, pos)
            self.msgs[user] = msg


class RoomTickerAdd(ServerMessage):
    """ Message 114 """
    def __init__(self):
        self.room = None
        self.user = None
        self.msg = None

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos, self.user = self.getObject(message, bytes, pos)
        pos, self.msg = self.getObject(message, bytes, pos)


class RoomTickerRemove(ServerMessage):
    """ Message 115 """
    def __init__(self, room=None):
        self.user = None
        self.room = _str(room)

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos, self.user = self.getObject(message, bytes, pos)


class RoomTickerSet(ServerMessage):
    """ Message 116 """
    def __init__(self, room=None, msg=""):
        self.room = _str(room)
        self.msg = _str(msg)

    def makeNetworkMessage(self):
        return self.packObject(self.room) + self.packObject(self.msg)


class ConnectToPeer(ServerMessage):
    """ Either we ask server to tell someone else we want to establish a
    connection with him or server tells us someone wants to connect with us.
    Used when the side that wants a connection can't establish it, and tries
    to go the other way around.
    """
    def __init__(self, token=None, user=None, type=None):
        self.token = token
        self.user = _str(user)
        self.type = _str(type)

    def makeNetworkMessage(self):
        return self.packObject(NetworkIntType(self.token)) + self.packObject(self.user) + self.packObject(self.type)

    def parseNetworkMessage(self, message):
        pos, self.user = self.getObject(message, bytes)
        pos, self.type = self.getObject(message, bytes, pos)
        import socket
        pos, self.ip = pos + 4, socket.inet_ntoa(message[pos:pos + 4][::-1])
        pos, self.port = self.getObject(message, int, pos, 1)
        pos, self.token = self.getObject(message, int, pos)
        if len(message[pos:]) > 0:
            # Don't know what this is, may be some kind of status
            pos, self.unknown = pos + 1, message[pos]


class MessageUser(ServerMessage):
    """ Chat phrase sent to someone or received by us in private"""
    def __init__(self, user=None, msg=None):
        self.user = _str(user)
        self.msg = _str(msg)

    def makeNetworkMessage(self):
        return self.packObject(self.user) + self.packObject(self.msg)

    def parseNetworkMessage(self, message):
        pos, self.msgid = self.getObject(message, int)
        pos, self.timestamp = self.getObject(message, int, pos)
        pos, self.user = self.getObject(message, bytes, pos)
        pos, self.msg = self.getObject(message, bytes, pos)


class MessageAcked(ServerMessage):
    """ Confirmation of private chat message.
    If we don't send it, the server will keep sending the chat phrase to us.
    """
    def __init__(self, msgid=None):
        self.msgid = msgid

    def makeNetworkMessage(self):
        return self.packObject(NetworkIntType(self.msgid))


class FileSearch(ServerMessage):
    """ We send this to the server when we search for something."""
    """ Server send this to tell us someone is searching for something."""
    def __init__(self, requestid=None, text=None):
        self.searchid = requestid
        self.searchterm = _str(text)
        if text:
            self.searchterm = ' '.join([x for x in text.split() if x != '-'])

    def makeNetworkMessage(self):
        return self.packObject(NetworkIntType(self.searchid)) + self.packObject(self.searchterm)

    def parseNetworkMessage(self, message):
        pos, self.user = self.getObject(message, bytes)
        pos, self.searchid = self.getObject(message, int, pos)
        pos, self.searchterm = self.getObject(message, bytes, pos)


class WishlistSearch(FileSearch):
    pass


class QueuedDownloads(ServerMessage):
    """ Server sends this to indicate if someone has download slots available
    or not. """
    def parseNetworkMessage(self, message):
        pos, self.user = self.getObject(message, bytes)
        pos, self.slotsfull = self.getObject(message, int, pos)


class SendSpeed(ServerMessage):
    """ We used to send this after a finished download to let the server update
    the speed statistics for a user"""
    def __init__(self, user=None, speed=None):
        self.user = _str(user)
        self.speed = speed

    def makeNetworkMessage(self):
        return self.packObject(self.user) + self.packObject(NetworkIntType(self.speed))


class SendUploadSpeed(ServerMessage):
    """ We now send this after a finished upload to let the server update
    the speed statistics for a user"""
    def __init__(self, speed=None):
        self.speed = speed

    def makeNetworkMessage(self):
        return self.packObject(NetworkIntType(self.speed))


class SharedFoldersFiles(ServerMessage):
    """ We send this to server to indicate the number of folder and files
    that we share """
    def __init__(self, folders=None, files=None):
        self.folders = folders
        self.files = files

    def makeNetworkMessage(self):
        return self.packObject(NetworkIntType(self.folders)) + self.packObject(NetworkIntType(self.files))


class GetUserStats(ServerMessage):
    """ Server sends this to indicate change in user's statistics"""
    def __init__(self, user=None):
        self.user = _str(user)
        self.country = None

    def makeNetworkMessage(self):
        return self.packObject(self.user)

    def parseNetworkMessage(self, message):
        pos, self.user = self.getObject(message, bytes)
        pos, self.avgspeed = self.getObject(message, int, pos, getsignedint=1)
        pos, self.downloadnum = self.getObject(message, int, pos, getsignedint=1)
        pos, self.files = self.getObject(message, int, pos)
        pos, self.dirs = self.getObject(message, int, pos)


class Relogged(ServerMessage):
    """ Message 41 """
    """ Server sends this if someone else logged in under our nickname
    and then disconnects us """
    def parseNetworkMessage(self, message):
        pass


class PlaceInLineResponse(ServerMessage):
    """ Server sends this to indicate change in place in queue while we're
    waiting for files from other peer """
    def __init__(self, user=None, req=None, place=None):
        self.req = req
        self.user = _str(user)
        self.place = place

    def makeNetworkMessage(self):
        return self.packObject(self.user) + self.packObject(NetworkIntType(self.req)) + self.packObject(NetworkIntType(self.place))

    def parseNetworkMessage(self, message):
        pos, self.user = self.getObject(message, bytes)
        pos, self.req = self.getObject(message, int, pos)
        pos, self.place = self.getObject(message, int, pos)


class RoomAdded(ServerMessage):
    """ Server tells us a new room has been added"""
    def parseNetworkMessage(self, message):
        self.room = self.getObject(message, bytes)[1]


class RoomRemoved(ServerMessage):
    """ Server tells us a room has been removed"""
    def parseNetworkMessage(self, message):
        self.room = self.getObject(message, bytes)[1]


class RoomList(ServerMessage):
    """ Server tells us a list of rooms"""
    def __init__(self):
        pass

    def makeNetworkMessage(self):
        return b""

    def parseNetworkMessage(self, message):
        pos, numrooms = self.getObject(message, int)
        self.rooms = []
        self.ownedprivaterooms = []
        self.otherprivaterooms = []
        for i in range(numrooms):
            pos, room = self.getObject(message, bytes, pos)
            self.rooms.append([room, None])
        pos, numusercounts = self.getObject(message, int, pos)
        for i in range(numusercounts):
            pos, usercount = self.getObject(message, int, pos)
            self.rooms[i][1] = usercount
        if len(message[pos:]) == 0:
            return
        (pos, self.ownedprivaterooms) = self._getRooms(pos, message)
        (pos, self.otherprivaterooms) = self._getRooms(pos, message)

    def _getRooms(self, originalpos, message):
        try:
            pos, numberofrooms = self.getObject(message, int, originalpos)
            rooms = []
            for i in range(numberofrooms):
                pos, room = self.getObject(message, bytes, pos)
                rooms.append([room, None])
            pos, numberofusers = self.getObject(message, int, pos)
            for i in range(numberofusers):
                pos, usercount = self.getObject(message, int, pos)
                rooms[i][1] = usercount
            return (pos, rooms)
        except Exception as error:
            log.addwarning(_("Exception during parsing %(area)s: %(exception)s") % {'area': 'RoomList', 'exception': error})
            return (originalpos, [])


class ExactFileSearch(ServerMessage):
    """ Someone is searching for a file with an exact name """
    def parseNetworkMessage(self, message):
        pos, self.user = self.getObject(message, bytes)
        pos, self.req = self.getObject(message, int, pos)
        pos, self.file = self.getObject(message, bytes, pos)
        pos, self.folder = self.getObject(message, bytes, pos)
        pos, self.size = self.getObject(message, int, pos, getsignedint=1)
        pos, self.checksum = self.getObject(message, int, pos)


class AdminMessage(ServerMessage):
    """ A global message from the admin has arrived """
    def parseNetworkMessage(self, message):
        self.msg = self.getObject(message, bytes)[1]


class GlobalUserList(JoinRoom):
    """ We send this to get a global list of all users online """
    def __init__(self):
        pass

    def makeNetworkMessage(self):
        return b""

    def parseNetworkMessage(self, message):
        pos, self.users = self.getUsers(message)


class TunneledMessage(ServerMessage):
    def __init__(self, user=None, req=None, code=None, msg=None):
        self.user = _str(user)
        self.req = req
        self.code = code
        self.msg = _str(msg)

    def makeNetworkMessage(self, message):
        return (self.packObject(self.user) +
                self.packObject(NetworkIntType(self.req)) +
                self.packObject(NetworkIntType(self.code)) +
                self.packObject(self.msg))

    def parseNetworkMessage(self, message):
        pos, self.user = self.getObject(message, bytes)
        pos, self.code = self.getObject(message, int, pos)
        pos, self.req = self.getObject(message, int, pos)
        pos, self.ip = pos + 4, socket.inet_ntoa(self.strrev(message[pos:pos + 4]))
        pos, port = self.getObject(message, int, pos, 1)
        self.addr = (self.ip, port)
        pos, self.msg = self.getObject(message, bytes, pos)


class ParentMinSpeed(ServerMessage):
    """ Message 83 """
    def __init__(self):
        pass

    def parseNetworkMessage(self, message):
        pos, self.num = self.getObject(message, int)


class ParentSpeedRatio(ParentMinSpeed):
    """ Message 84 """
    def __init__(self):
        pass

    def parseNetworkMessage(self, message):
        pos, self.num = self.getObject(message, int)


class SearchParent(ServerMessage):
    """ Message 73 """
    def __init__(self, parentip=None):
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
        pos, self.seconds = self.getObject(message, int)


class SearchInactivityTimeout(ServerMessage):
    # 87
    def __init__(self):
        pass

    def parseNetworkMessage(self, message):
        pos, self.seconds = self.getObject(message, int)


class MinParentsInCache(ServerMessage):
    def __init__(self):
        pass

    def parseNetworkMessage(self, message):
        pos, self.num = self.getObject(message, int)


class Msg12547(ServerMessage):
    def __init__(self, conn):
        self.conn = conn

    def parseNetworkMessage(self, message):
        pass


class UploadQueueNotification(PeerMessage):
    def __init__(self, conn):
        self.conn = conn

    def makeNetworkMessage(self):
        return b""

    def parseNetworkMessage(self, message):
        return b""


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
        pos, self.seconds = self.getObject(message, int)


class WishlistInterval(ServerMessage):
    """ Message 104"""
    def __init__(self):
        pass

    def parseNetworkMessage(self, message):
        pos, self.seconds = self.getObject(message, int)


class PrivilegedUsers(ServerMessage):
    """ Message 69 """
    """ A list of those who made a donation """
    def __init__(self):
        pass

    def parseNetworkMessage(self, message):
        try:
            x = zlib.decompress(message)
            message = x[4:]
        except Exception as error:  # noqa: F841
            pass
        self.users = []
        pos, numusers = self.getObject(message, int)
        for i in range(numusers):
            pos, user = self.getObject(message, bytes, pos)
            self.users.append(user)


class CheckPrivileges(ServerMessage):
    """ Message 92 """
    def __init__(self):
        pass

    def makeNetworkMessage(self):
        return b""

    def parseNetworkMessage(self, message):
        pos, self.seconds = self.getObject(message, int)


class AddToPrivileged(ServerMessage):
    """ Message 91 """
    def __init__(self):
        pass

    def parseNetworkMessage(self, message):
        l2, self.user = self.getObject(message, bytes)


class CantConnectToPeer(ServerMessage):
    """ Message 1001 """
    """ We send this to say we can't connect to peer after it has asked us
    to connect. We receive this if we asked peer to connect and it can't do
    this. So this message means a connection can't be established either way.
    """
    def __init__(self, token=None, user=None):
        self.token = token
        self.user = _str(user)

    def makeNetworkMessage(self):
        return (self.packObject(NetworkIntType(self.token)) +
                self.packObject(self.user))

    def parseNetworkMessage(self, message):
        pos, self.token = self.getObject(message, int)


# class CantCreateRoom(ServerMessage):
    # """ Server tells us a new room cannot be created"""
    # def parseNetworkMessage(self, message):
        # self.room = self.getObject(message, types.StringType)[1]


class ServerPing(ServerMessage):
    """ Message 32 """
    def makeNetworkMessage(self):
        return b""

    def parseNetworkMessage(self, message):
        pass


class AddThingILike(ServerMessage):
    """ Add item to our likes list """
    def __init__(self, thing=None):
        self.thing = _str(thing)

    def makeNetworkMessage(self):
        return self.packObject(self.thing)


class AddThingIHate(AddThingILike):
    pass


class RemoveThingILike(ServerMessage):
    """ Remove item from our likes list """
    def __init__(self, thing=None):
        self.thing = _str(thing)

    def makeNetworkMessage(self):
        return self.packObject(self.thing)


class RemoveThingIHate(RemoveThingILike):
    pass


class UserInterests(ServerMessage):
    def __init__(self, user=None):
        self.user = _str(user)
        self.likes = None
        self.hates = None

    def makeNetworkMessage(self):
        # Request a users' interests
        return self.packObject(self.user)

    def parseNetworkMessage(self, message, pos=0):
        # Receive a users' interests
        pos, self.user = self.getObject(message, bytes, pos)
        pos, likesnum = self.getObject(message, int, pos)
        self.likes = []
        for i in range(likesnum):
            pos, key = self.getObject(message, bytes, pos)
            self.likes.append(key)

        pos, hatesnum = self.getObject(message, int, pos)
        self.hates = []
        for i in range(hatesnum):
            pos, key = self.getObject(message, bytes, pos)
            self.hates.append(key)


class GlobalRecommendations(ServerMessage):
    def __init__(self):
        self.recommendations = None
        self.unrecommendations = None

    def makeNetworkMessage(self):
        return b""

    def parseNetworkMessage(self, message):
        self.unpack_recommendations(message)

    def unpack_recommendations(self, message, pos=0):
        self.recommendations = {}
        self.unrecommendations = {}
        pos, num = self.getObject(message, int, pos)
        for i in range(num):
            pos, key = self.getObject(message, bytes, pos)
            pos, rating = self.getObject(message, int, pos, getsignedint=1)
            self.recommendations[key] = rating

        if len(message[pos:]) == 0:
            return

        pos, num2 = self.getObject(message, int, pos)
        for i in range(num2):
            pos, key = self.getObject(message, bytes, pos)
            pos, rating = self.getObject(message, int, pos, getsignedint=1)
            self.unrecommendations[key] = rating


class Recommendations(GlobalRecommendations):
    pass


class ItemRecommendations(GlobalRecommendations):
    def __init__(self, thing=None):
        GlobalRecommendations.__init__(self)
        self.thing = _str(thing)

    def makeNetworkMessage(self):
        return self.packObject(self.thing)

    def parseNetworkMessage(self, message):
        pos, self.thing = self.getObject(message, bytes)
        self.unpack_recommendations(message, pos)


class SimilarUsers(ServerMessage):
    def __init__(self):
        self.users = None

    def makeNetworkMessage(self):
        return b""

    def parseNetworkMessage(self, message):
        self.users = {}
        pos, num = self.getObject(message, int)
        for i in range(num):
            pos, user = self.getObject(message, bytes, pos)
            pos, rating = self.getObject(message, int, pos)
            self.users[user] = rating


class ItemSimilarUsers(ServerMessage):
    def __init__(self, thing=None):
        self.thing = _str(thing)
        self.users = None

    def makeNetworkMessage(self):
        return self.packObject(self.thing)

    def parseNetworkMessage(self, message):
        self.users = []
        pos, self.thing = self.getObject(message, bytes)
        pos, num = self.getObject(message, int, pos)
        for i in range(num):
            pos, user = self.getObject(message, bytes, pos)
            self.users.append(user)


class RoomSearch(ServerMessage):
    def __init__(self, room=None, requestid=None, text=""):
        self.room = _str(room)
        self.searchid = requestid
        self.searchterm = ' '.join([x for x in _str(text.split()) if x != '-'])

    def makeNetworkMessage(self):
        return (self.packObject(self.room) +
                self.packObject(NetworkIntType(self.searchid)) +
                self.packObject(self.searchterm))

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos, self.searchid = self.getObject(message, int, pos)
        pos, self.searchterm = self.getObject(message, bytes, pos)

    def __repr__(self):
        return "RoomSearch(room=%s, requestid=%s, text=%s)" % (self.room, self.searchid, self.searchterm)


class UserSearch(ServerMessage):
    def __init__(self, user=None, requestid=None, text=None):
        self.suser = _str(user)
        self.searchid = requestid
        self.searchterm = _str(text)

    def makeNetworkMessage(self):
        return (self.packObject(self.suser) +
                self.packObject(NetworkIntType(self.searchid)) +
                self.packObject(self.searchterm))

    def parseNetworkMessage(self, message):
        pos, self.user = self.getObject(message, bytes)
        pos, self.searchid = self.getObject(message, int, pos)
        pos, self.searchterm = self.getObject(message, bytes, pos)


class PierceFireWall(PeerMessage):
    """ This is the very first message send by peer that established a
    connection, if it has been asked by other peer to do so. Token is taken
    from ConnectToPeer server message."""
    def __init__(self, conn, token=None):
        self.conn = conn
        self.token = token

    def makeNetworkMessage(self):
        return self.packObject(NetworkIntType(self.token))

    def parseNetworkMessage(self, message):
        pos, self.token = self.getObject(message, int)


class PeerInit(PeerMessage):
    """ This message is sent by peer that initiated a connection, not
    necessarily a peer that actually established it. Token apparently
    can be anything. Type is 'P' if it's anything but filetransfer, 'F'
    otherwise"""
    def __init__(self, conn, user=None, type=None, token=None):
        self.conn = conn
        self.user = _str(user)
        self.type = _str(type)
        self.token = token

    def makeNetworkMessage(self):
        return (self.packObject(self.user) +
                self.packObject(self.type) +
                self.packObject(NetworkIntType(self.token)))

    def parseNetworkMessage(self, message):
        pos, self.user = self.getObject(message, bytes)
        pos, self.type = self.getObject(message, bytes, pos)
        pos, self.token = self.getObject(message, int, pos)


class PMessageUser(PeerMessage):
    """ Chat phrase sent to someone or received by us in private"""
    def __init__(self, conn=None, user=None, msg=None):
        self.conn = conn
        self.user = _str(user)
        self.msg = _str(msg)

    def makeNetworkMessage(self):
        return (self.packObject(0) +
                self.packObject(0) +
                self.packObject(self.user) +
                self.packObject(self.msg))

    def parseNetworkMessage(self, message):
        pos, self.msgid = self.getObject(message, int)
        pos, self.timestamp = self.getObject(message, int, pos)
        pos, self.user = self.getObject(message, bytes, pos)
        pos, self.msg = self.getObject(message, bytes, pos)


class UserInfoRequest(PeerMessage):
    """ Ask other peer to send user information, picture and all."""
    def __init__(self, conn):
        self.conn = conn

    def makeNetworkMessage(self):
        return b""

    def parseNetworkMessage(self, message):
        pass


class UserInfoReply(PeerMessage):
    """ Peer responds with this, when asked for user information."""
    def __init__(self, conn, descr=None, pic=None, totalupl=None, queuesize=None, slotsavail=None, uploadallowed=None):
        self.conn = conn
        self.descr = _str(descr)
        self.pic = _str(pic)
        self.totalupl = totalupl
        self.queuesize = queuesize
        self.slotsavail = slotsavail
        self.uploadallowed = uploadallowed

    def parseNetworkMessage(self, message):
        pos, self.descr = self.getObject(message, bytes)
        pos, self.has_pic = pos + 1, message[pos]
        if self.has_pic:
            pos, self.pic = self.getObject(message, bytes, pos)
        pos, self.totalupl = self.getObject(message, int, pos)
        pos, self.queuesize = self.getObject(message, int, pos)
        pos, self.slotsavail = pos + 1, message[pos]

        if len(message[pos:]) >= 4:
            pos, self.uploadallowed = self.getObject(message, int, pos)

    def makeNetworkMessage(self):
        if self.pic is not None:
            pic = chr(1) + self.packObject(self.pic)
        else:
            pic = chr(0)

        return (self.packObject(self.descr) +
                pic +
                self.packObject(NetworkIntType(self.totalupl)) +
                self.packObject(NetworkIntType(self.queuesize)) +
                chr(self.slotsavail) +
                self.packObject(NetworkIntType(self.uploadallowed)))


class SharedFileList(PeerMessage):
    """ Peer responds with this when asked for a filelist."""
    def __init__(self, conn, shares=None):
        self.conn = conn
        self.list = shares
        self.built = None

    def parseNetworkMessage(self, message, nozlib=False):
        if not nozlib:
            try:
                message = zlib.decompress(message)
            except Exception as error:
                log.addwarning(_("Exception during parsing %(area)s: %(exception)s") % {'area': 'SharedFileList', 'exception': error})
                self.list = {}
                return
        if not self.doubleParseNetworkMessage(message):
            self.list = {}

    def _parseNetworkMessage(self, message, sizetype):
        shares = []
        pos, ndir = self.getObject(message, int)
        for i in range(ndir):
            pos, directory = self.getObject(message, bytes, pos)
            pos, nfiles = self.getObject(message, int, pos)
            files = []
            for j in range(nfiles):
                pos, code = pos + 1, message[pos]
                pos, name = self.getObject(message, bytes, pos)
                pos, size = self.getObject(message, sizetype, pos, getsignedint=True, printerror=False)
                if message[pos - 1] == '\xff':
                    # Buggy SLSK?
                    # Some file sizes will be huge if unpacked as a signed
                    # LongType, namely somewhere in the area of 17179869 Terabytes.
                    # It would seem these files are indeed big, but in the Gigabyte range.
                    # The following will undo the damage (and if we fuck up it
                    # doesn't matter, it can never be worse than reporting 17
                    # exabytes for a single file)
                    size = struct.unpack("Q", '\xff' * struct.calcsize("Q"))[0] - size
                pos, ext = self.getObject(message, bytes, pos, printerror=False)
                pos, numattr = self.getObject(message, int, pos, printerror=False)
                attrs = []
                for k in range(numattr):
                    pos, attrnum = self.getObject(message, int, pos, printerror=False)
                    pos, attr = self.getObject(message, int, pos, printerror=False)
                    attrs.append(attr)
                files.append([code, name, size, ext, attrs])
            shares.append((directory, files))
        self.list = shares

    def makeNetworkMessage(self, nozlib=0, rebuild=False):
        # Elaborate hack, to save CPU
        # Store packed message contents in self.built, and use
        # instead of repacking it, unless rebuild is True
        if not rebuild and self.built is not None:
            return self.built
        msg = b""
        msg = msg + self.packObject(len(list(self.list.keys())))
        for (key, value) in self.list.items():
            msg = msg + self.packObject(key.replace(os.sep, "\\")) + value
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
        return b""


class FileSearchRequest(PeerMessage):
    """ We send this to the peer when we search for something."""
    """ Peer sends this to tell us he is  searching for something."""
    def __init__(self, conn, requestid=None, text=None):
        self.conn = conn
        self.requestid = requestid
        self.text = _str(text)

    def makeNetworkMessage(self):
        return self.packObject(NetworkIntType(self.requestid)) + self.packObject(self.text)

    def parseNetworkMessage(self, message):
        pos, self.searchid = self.getObject(message, int)
        pos, self.searchterm = self.getObject(message, bytes, pos)


class FileSearchResult(PeerMessage):
    """ Peer sends this when it has a file search match."""
    def __init__(self, conn, user=None, geoip=None, token=None, shares=None, fileindex=None, freeulslots=None, ulspeed=None, inqueue=None, fifoqueue=None):
        self.conn = conn
        self.user = _str(user)
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
        self.pos, self.user = self.getObject(message, bytes)
        self.pos, self.token = self.getObject(message, int, self.pos)
        self.pos, nfiles = self.getObject(message, int, self.pos)
        shares = []
        for i in range(nfiles):
            self.pos, code = self.pos + 1, message[self.pos]
            self.pos, name = self.getObject(message, bytes, self.pos)
            # suppressing errors with unpacking, can be caused by incorrect sizetype
            self.pos, size = self.getObject(message, sizetype, self.pos, printerror=False)
            self.pos, ext = self.getObject(message, bytes, self.pos, printerror=False)
            self.pos, numattr = self.getObject(message, int, self.pos, printerror=False)
            attrs = []
            if numattr:
                for j in range(numattr):
                    self.pos, attrnum = self.getObject(message, int, self.pos, printerror=False)
                    self.pos, attr = self.getObject(message, int, self.pos, printerror=False)
                    attrs.append(attr)
            shares.append([code, name, size, ext, attrs])
        self.list = shares
        self.pos, self.freeulslots = self.pos + 1, message[self.pos]
        self.pos, self.ulspeed = self.getObject(message, int, self.pos, getsignedint=1)
        self.pos, self.inqueue = self.getObject(message, int, self.pos)

    def makeNetworkMessage(self):
        filelist = []
        for i in self.list:
            try:
                filelist.append(self.fileindex[str(i)])
            except Exception:
                pass

        queuesize = self.inqueue[0]

        msg = (self.packObject(self.user) +
               self.packObject(NetworkIntType(self.token)) +
               self.packObject(NetworkIntType(len(filelist))))
        for i in filelist:
            msg += (chr(1) +
                    self.packObject(i[0]. replace(os. sep, "\\")) +
                    self.packObject(NetworkLongLongType(i[1])))
            if i[2] is None:
                # No metadata
                msg += self.packObject('') + self.packObject(0)
            else:
                # FileExtension, NumAttributes,
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
    def __init__(self, conn, directory=None):
        self.conn = conn
        self.dir = _str(directory)

    def makeNetworkMessage(self):
        return self.packObject(1) + self.packObject(self.dir)

    def parseNetworkMessage(self, message):
        pos, self.something = self.getObject(message, int)
        pos, self.dir = self.getObject(message, bytes, pos)


class FolderContentsResponse(PeerMessage):
    """ Peer tells us the contents of a particular folder (with all subfolders)
    """
    def __init__(self, conn, directory=None, shares=None):
        self.conn = conn
        self.dir = _str(directory)
        self.list = shares

    def parseNetworkMessage(self, message):
        try:
            message = zlib.decompress(message)
        except Exception as error:
            log.addwarning(_("Exception during parsing %(area)s: %(exception)s") % {'area': 'FolderContentsResponse', 'exception': error})
            self.list = {}
            return
        if not self.doubleParseNetworkMessage(message):
            self.list = {}

    def _parseNetworkMessage(self, message, sizetype):
        shares = {}
        pos, nfolders = self.getObject(message, int)
        for h in range(nfolders):
            pos, folder = self.getObject(message, bytes, pos)
            shares[folder] = {}
            pos, ndir = self.getObject(message, int, pos)

            for i in range(ndir):
                pos, directory = self.getObject(message, bytes, pos)
                pos, nfiles = self.getObject(message, int, pos)
                shares[folder][directory] = []
                for j in range(nfiles):
                    pos, code = pos + 1, message[pos]
                    pos, name = self.getObject(message, bytes, pos, printerror=False)
                    pos, size = self.getObject(message, sizetype, pos, getsignedint=1, printerror=False)
                    pos, ext = self.getObject(message, bytes, pos, printerror=False)
                    pos, numattr = self.getObject(message, int, pos, printerror=False)
                    attrs = []
                    for k in range(numattr):
                        pos, attrnum = self.getObject(message, int, pos, printerror=False)
                        pos, attr = self.getObject(message, int, pos, printerror=False)
                        attrs.append(attr)
                    shares[folder][directory].append([code, name, size, ext, attrs])
        self.list = shares

    def makeNetworkMessage(self):
        msg = self.packObject(1) + self.packObject(self.dir) + self.packObject(1) + self.packObject(self.dir) + self.packObject(len(self.list))
        for i in self.list:
            msg = msg + chr(1) + self.packObject(i[0]) + self.packObject(i[1]) + self.packObject(0)
            if i[2] is None:
                msg = msg + self.packObject('') + self.packObject(0)
            else:
                msg = msg + self.packObject("mp3") + self.packObject(3)
                msg = msg + self.packObject(0) + self.packObject(i[2][0]) + self.packObject(1) + self.packObject(i[3]) + self.packObject(2) + self.packObject(i[2][1])
        return zlib.compress(msg)


class TransferRequest(PeerMessage):
    """ Request a file from peer, or tell a peer that we want to send a file to
    them. """
    def __init__(self, conn, direction=None, req=None, file=None, filesize=None, realfile=None):
        self.conn = conn
        self.direction = direction
        self.req = req
        self.file = _str(file)  # virtual file
        self.realfile = realfile
        self.filesize = filesize

    def makeNetworkMessage(self):
        msg = self.packObject(self.direction) + self.packObject(self.req) + self.packObject(self.file)
        if self.filesize is not None and self.direction == 1:
            msg = msg + self.packObject(NetworkLongLongType(self.filesize))
        return msg

    def parseNetworkMessage(self, message):
        pos, self.direction = self.getObject(message, int)
        pos, self.req = self.getObject(message, int, pos)
        pos, self.file = self.getObject(message, bytes, pos)
        if self.direction == 1:
            pos, self.filesize = self.getObject(message, int, pos)


class TransferResponse(PeerMessage):
    """ Response to the TreansferRequest - either we (or other peer) agrees, or
    tells the reason for rejecting filetransfer. """
    def __init__(self, conn, allowed=None, reason=None, req=None, filesize=None):
        self.conn = conn
        self.allowed = allowed
        self.req = req
        self.reason = _str(reason)
        self.filesize = filesize

    def makeNetworkMessage(self):
        msg = self.packObject(NetworkIntType(self.req)) + bytes([self.allowed])
        if self.reason is not None:
            msg = msg + self.packObject(self.reason)
        if self.filesize is not None:
            msg = msg + self.packObject(NetworkLongLongType(self.filesize))
        return msg

    def parseNetworkMessage(self, message):
        pos, self.req = self.getObject(message, int)
        pos, self.allowed = pos + 1, message[pos]
        if message[pos:] != "":
            if self.allowed:
                pos, self.filesize = self.getObject(message, int, pos)
            else:
                pos, self.reason = self.getObject(message, bytes, pos)


class PlaceholdUpload(PeerMessage):
    def __init__(self, conn, file=None):
        self.conn = conn
        self.file = _str(file)

    def makeNetworkMessage(self):
        return self.packObject(self.file)

    def parseNetworkMessage(self, message):
        pos, self.file = self.getObject(message, bytes)


class QueueUpload(PlaceholdUpload):
    pass


class UploadFailed(PlaceholdUpload):
    pass


class PlaceInQueue(PeerMessage):
    def __init__(self, conn, filename=None, place=None):
        self.conn = conn
        self.filename = _str(filename)
        self.place = place

    def makeNetworkMessage(self):
        return self.packObject(self.filename) + self.packObject(NetworkIntType(self.place))

    def parseNetworkMessage(self, message):
        pos, self.filename = self.getObject(message, bytes)
        pos, self.place = self.getObject(message, int, pos)


class PlaceInQueueRequest(PlaceholdUpload):
    pass


class QueueFailed(PeerMessage):
    def __init__(self, conn, file=None, reason=None):
        self.conn = conn
        self.file = _str(file)
        self.reason = _str(reason)

    def makeNetworkMessage(self):
        return self.packObject(self.file) + self.packObject(self.reason)

    def parseNetworkMessage(self, message):
        pos, self.file = self.getObject(message, bytes)
        pos, self.reason = self.getObject(message, bytes, pos)


class FileRequest(PeerMessage):
    """ Request a file from peer, or tell a peer that we want to send a file to
    them. """
    def __init__(self, conn, req=None):
        self.conn = conn
        self.req = _str(req)

    def makeNetworkMessage(self):
        msg = self.packObject(self.req)
        return msg


class HaveNoParent(ServerMessage):  # 71
    def __init__(self, noparent=None):
        self.noparent = noparent

    def makeNetworkMessage(self):
        return bytes((self.noparent,))


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
            log.addwarning('Hitme')
            return False

    def _parseNetworkMessage(self, message, sizetype):
        pos, self.something = self.getObject(message, sizetype, printerror=False)
        pos, self.user = self.getObject(message, bytes, pos, printerror=False)
        pos, self.searchid = self.getObject(message, sizetype, pos, printerror=False)
        pos, self.searchterm = self.getObject(message, bytes, pos, printerror=False)


class DistribBranchLevel(DistribMessage):
    def __init__(self, conn):
        self.conn = conn

    def parseNetworkMessage(self, message):
        pos, self.value = self.getObject(message, int)
        # print message.__repr__()


class DistribBranchRoot(DistribMessage):
    def __init__(self, conn):
        self.conn = conn

    def parseNetworkMessage(self, message):
        # pos, self.value = self.getObject(message, types.IntType)
        pos, self.user = self.getObject(message, bytes)
        # print self.something, self.user


class DistribChildDepth(DistribMessage):
    def __init__(self, conn):
        self.conn = conn

    def parseNetworkMessage(self, message):
        pos, self.value = self.getObject(message, int)
        # print self.something, self.user


class DistribMessage9(DistribMessage):
    def __init__(self, conn):
        self.conn = conn

    def parseNetworkMessage(self, message):
        # pos, self.value = self.getObject(message, types.IntType)
        try:
            x = zlib.decompress(message)  # noqa: F841
        except Exception:
            self.debug()
        # message =  x[4:]
        # pos, self.user = self.getObject(message, types.StringType)
        # self.debug()
        # print self.something, self.user


class BranchLevel(ServerMessage):
    def __init__(self):
        pass

    def parseNetworkMessage(self, message):
        pos, self.value = self.getObject(message, int)
        # print message.__repr__()


class BranchRoot(ServerMessage):
    def __init__(self):
        pass

    def parseNetworkMessage(self, message):
        # pos, self.value = self.getObject(message, types.IntType)
        pos, self.user = self.getObject(message, bytes)
        # print self.something, self.user


class AcceptChildren(ServerMessage):
    def __init__(self, enabled=None):
        self.enabled = enabled

    def makeNetworkMessage(self):
        return chr(self.enabled)


class ChildDepth(ServerMessage):
    def __init__(self):
        pass

    def parseNetworkMessage(self, message):
        pos, self.value = self.getObject(message, int)


class NetInfo(ServerMessage):
    """ Information about what nodes have been added/removed in the network """
    def __init__(self):
        pass

    def parseNetworkMessage(self, message: bytes):
        self.list = {}
        pos, num = self.getObject(message, int)
        for i in range(num):
            pos, username = self.getObject(message, bytes, pos)
            pos, self.ip = pos + 4, socket.inet_ntoa(message[pos:pos + 4][::-1])
            pos, port = self.getObject(message, int, pos)
            self.list[username] = (self.ip, port)


class SearchRequest(ServerMessage):
    """ Search request that arrives through the server"""
    def __init__(self):
        pass

    def parseNetworkMessage(self, message):
        pos, self.code = 1, message[0]
        pos, self.something = self.getObject(message, int, pos)
        pos, self.user = self.getObject(message, bytes, pos)
        pos, self.searchid = self.getObject(message, int, pos)
        pos, self.searchterm = self.getObject(message, bytes, pos)


class UserPrivileged(ServerMessage):
    """ Discover whether a user is privileged or not """
    def __init__(self, user=None):
        self.user = _str(user)
        self.privileged = None

    def makeNetworkMessage(self):
        return self.packObject(self.user)

    def parseNetworkMessage(self, message):
        pos, self.user = self.getObject(message, bytes, 0)  # noqa: F821
        pos, self.privileged = pos + 1, bool(message[pos])


class GivePrivileges(ServerMessage):
    """ Give (part) of your privileges to another user on the network """
    def __init__(self, user=None, days=None):
        self.user = _str(user)
        self.days = days

    def makeNetworkMessage(self):
        return self.packObject(self.user) + self.packObject(self.days)


class PopupMessage:
    """For messages that should be shown to the user prominently, for example
    through a popup. Should be used sparsely."""
    def __init__(self, title, message):
        self.title = _str(title)
        self.message = _str(message)
