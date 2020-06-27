# Copyright (C) 2020 Nicotine+ Team
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

import hashlib
import os
import socket
import struct
import zlib
from gettext import gettext as _
from itertools import count

from pynicotine.logfacility import log
from pynicotine.utils import debug
from pynicotine.utils import findBestEncoding

""" This module contains message classes, that networking and UI thread
exchange. Basically there are three types of messages: internal messages,
server messages and p2p messages (between clients)."""

counter = count(100)


def newId():
    global counter
    Id = next(counter)
    return Id


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
        return '{}: {} {} {}'.format(type(self).__name__, self.conn, self.addr, self.init)


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
        self.msg = msg


class DownloadFile(InternalMessage):
    """ Sent by networking thread to indicate file transfer progress.
    Sent by UI to pass the file object to write and offset to resume download
    from. """
    def __init__(self, conn=None, offset=None, file=None, filesize=None):
        self.conn = conn
        self.offset = offset
        self.file = file
        self.filesize = filesize


class UploadFile(InternalMessage):
    def __init__(self, conn=None, file=None, size=None, sentbytes=0, offset=None):
        self.conn = conn
        self.file = file
        self.size = size
        self.sentbytes = sentbytes
        self.offset = offset


class FileError(InternalMessage):
    """ Sent by networking thread to indicate that a file error occurred during
    filetransfer. """
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
        self.msg = msg
        self.debugLevel = debugLevel


class SlskMessage:
    """ This is a parent class for all protocol messages. """
    def getObject(self, message, type, start=0, getintasshort=0, getsignedint=0, printerror=True, rawbytes=False):
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
                length = struct.unpack("<I", message[start:start + intsize].ljust(intsize, b'\0'))[0]
                string = message[start + intsize:start + length + intsize]

                if rawbytes is False:
                    string = findBestEncoding(string, ['utf-8', 'iso-8859-1'])

                return length + intsize + start, string
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
    """ Server code: 1 """
    """ We sent this to the server right after the connection has been
    established. Server responds with the greeting message. """

    def __init__(self, username=None, passwd=None, version=None):
        self.username = username
        self.passwd = passwd
        self.version = version
        self.ip = None

    def __repr__(self):
        return 'Login({}, {}, {})'.format(self.username, self.version, self.ip)

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
    """ Server code: 142 """
    """ We send this to the server to change our password. We receive a
    response if our password changes. """

    def __init__(self, password=None):
        self.password = password

    def makeNetworkMessage(self):
        return self.packObject(self.password)

    def parseNetworkMessage(self, message):
        pos, self.password = self.getObject(message, bytes)


class SetWaitPort(ServerMessage):
    """ Server code: 2 """
    """ We send this to the server to indicate the port number that we
    listen on (2234 by default). """
    def __init__(self, port=None):
        self.port = port

    def __repr__(self):
        return 'SetWaitPort({})'.format(self.port)

    def makeNetworkMessage(self):
        return self.packObject(NetworkIntType(self.port))


class GetPeerAddress(ServerMessage):
    """ Server code: 3 """
    """ We send this to the server to ask for a peer's address
    (IP address and port), given the peer's username. """
    def __init__(self, user=None):
        self.user = user

    def makeNetworkMessage(self):
        return self.packObject(self.user)

    def parseNetworkMessage(self, message):
        pos, self.user = self.getObject(message, bytes)
        import socket
        pos, self.ip = pos + 4, socket.inet_ntoa(message[pos:pos + 4][::-1])
        pos, self.port = self.getObject(message, int, pos, 1)


class AddUser(ServerMessage):
    """ Server code: 5 """
    """ Used to be kept updated about a user's status. """
    def __init__(self, user=None):
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
        pos, self.user = self.getObject(message, bytes)
        pos, self.userexists = pos + 1, message[pos]
        if message[pos:]:
            pos, self.status = self.getObject(message, int, pos)
            pos, self.avgspeed = self.getObject(message, int, pos)
            pos, self.downloadnum = self.getObject(message, NetworkLongLongType, pos)

            pos, self.files = self.getObject(message, int, pos)
            pos, self.dirs = self.getObject(message, int, pos)

            if message[pos:]:
                pos, self.country = self.getObject(message, bytes, pos)


class Unknown6(ServerMessage):
    """ Server code: 6 """
    """ UNKNOWN """
    def __init__(self, user=None):
        self.user = user

    def makeNetworkMessage(self):
        return self.packObject(self.user)

    def parseNetworkMessage(self, message):
        self.debug()
        pass


class RemoveUser(ServerMessage):
    """ Used when we no longer want to be kept updated about a user's status.
    (is this used anywhere?) """
    def __init__(self, user=None):
        self.user = user

    def makeNetworkMessage(self):
        return self.packObject(self.user)


class GetUserStatus(ServerMessage):
    """ Server code: 7 """
    """ The server tells us if a user has gone away or has returned. """
    def __init__(self, user=None):
        self.user = user
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
    """ Server code: 28 """
    """ We send our new status to the server. Status is a way to define whether
    you're available or busy.

    -1 = Unknown
    0 = Offline
    1 = Away
    2 = Online
    """
    def __init__(self, status=None):
        self.status = status

    def makeNetworkMessage(self):
        return self.packObject(self.status)


class NotifyPrivileges(ServerMessage):
    """ Server code: 124 """
    """ Server tells us something about privileges. """
    def __init__(self, token=None, user=None):
        self.token = token
        self.user = user

    def parseNetworkMessage(self, message):
        pos, self.token = self.getObject(message, int)
        pos, self.user = self.getObject(message, bytes, pos)

    def makeNetworkMessage(self):
        return self.packObject(self.token) + self.packObject(self.user)


class AckNotifyPrivileges(ServerMessage):
    """ Server code: 125 """
    def __init__(self, token=None):
        self.token = token

    def parseNetworkMessage(self, message):
        pos, self.token = self.getObject(message, int)

    def makeNetworkMessage(self):
        return self.packObject(NetworkIntType(self.token))


class JoinPublicRoom(ServerMessage):
    """ Server code: 150 """
    """ We ask the server to send us messages from all public rooms, also
    known as public chat. """
    def makeNetworkMessage(self):
        return b""


class LeavePublicRoom(ServerMessage):
    """ Server code: 151 """
    """ We ask the server to stop sending us messages from all public rooms,
    also known as public chat. """
    def makeNetworkMessage(self):
        return b""


class PublicRoomMessage(ServerMessage):
    """ Server code: 152 """
    """ The server sends this when a new message has been written in a public
    room (every single line written in every public room). """
    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos, self.user = self.getObject(message, bytes, pos)
        pos, self.msg = self.getObject(message, bytes, pos)


class SayChatroom(ServerMessage):
    """ Server code: 13 """
    """ Either we want to say something in the chatroom, or someone else did. """
    def __init__(self, room=None, msg=None):
        self.room = room
        self.msg = msg

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
    """ Server code: 14 """
    """ Server sends us this message when we join a room. Contains users list
    with data on everyone. """
    def __init__(self, room=None, private=None):
        self.room = room
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
    """ Server code: 133 """
    """ The server sends us a list of room users that we can alter
    (add operator abilities / dismember). """
    def __init__(self, room=None, numusers=None, users=None):
        self.room = room
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
    """ Server code: 148 """
    """ The server sends us a list of operators in a specific room, that we can
    remove operator abilities from. """
    def __init__(self, room=None, number=None):
        self.room = room
        self.number = number

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos, self.number = self.getObject(message, int, pos)
        self.operators = []
        for i in range(self.number):
            pos, user = self.getObject(message, bytes, pos)
            self.operators.append(user)


class PrivateRoomAddUser(ServerMessage):
    """ Server code: 134 """
    """ We send this to inform the server that we've added a user to a private room. """
    def __init__(self, room=None, user=None):
        self.room = room
        self.user = user

    def makeNetworkMessage(self):
        return self.packObject(self.room) + self.packObject(self.user)

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos, self.user = self.getObject(message, bytes, pos)


class PrivateRoomDismember(ServerMessage):
    """ Server code: 136 """
    """ We send this to the server to remove our own membership of a private room. """
    def __init__(self, room=None):
        self.room = room

    def makeNetworkMessage(self):
        return self.packObject(self.room)


class PrivateRoomDisown(ServerMessage):
    """ Server code: 137 """
    """ We send this to the server to stop owning a private room. """
    def __init__(self, room=None):
        self.room = room

    def makeNetworkMessage(self):
        return self.packObject(self.room)


class PrivateRoomSomething(ServerMessage):
    """ Server code: 138 """
    """ UNKNOWN """
    def __init__(self, room=None):
        self.room = room

    def makeNetworkMessage(self):
        return self.packObject(self.room)

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        self.debug()


class PrivateRoomRemoveUser(ServerMessage):
    """ Server code: 135 """
    """ We send this to inform the server that we've removed a user from a private room. """
    def __init__(self, room=None, user=None):
        self.room = room
        self.user = user

    def makeNetworkMessage(self):
        return self.packObject(self.room) + self.packObject(self.user)

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos, self.user = self.getObject(message, bytes, pos)


class PrivateRoomAdded(ServerMessage):
    """ Server code: 139 """
    """ The server sends us this message when we are added to a private room. """
    def __init__(self, room=None):
        self.room = room

    def parseNetworkMessage(self, message):
        self.room = self.getObject(message, bytes)[1]


class PrivateRoomRemoved(ServerMessage):
    """ Server code: 140 """
    """ The server sends us this message when we are removed from a private room. """
    def __init__(self, room=None):
        self.room = room

    def parseNetworkMessage(self, message):
        self.room = self.getObject(message, bytes)[1]


class PrivateRoomToggle(ServerMessage):
    """ Server code: 141 """
    """ We send this when we want to enable or disable invitations to private rooms. """
    def __init__(self, enabled=None):
        self.enabled = None if enabled is None else int(enabled)

    def makeNetworkMessage(self):
        return bytes((self.enabled,))

    def parseNetworkMessage(self, message):
        # When this is received, we store it in the config, and disable the appropriate menu item
        pos, self.enabled = 1, bool(int(message[0]))  # noqa: F841


class PrivateRoomAddOperator(ServerMessage):
    """ Server code: 143 """
    """ We send this to the server to add private room operator abilities to a user. """
    def __init__(self, room=None, user=None):
        self.room = room
        self.user = user

    def makeNetworkMessage(self):
        return self.packObject(self.room) + self.packObject(self.user)

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos, self.user = self.getObject(message, bytes, pos)


class PrivateRoomRemoveOperator(ServerMessage):
    """ Server code: 144 """
    """ We send this to the server to remove private room operator abilities from a user. """
    def __init__(self, room=None, user=None):
        self.room = room
        self.user = user

    def makeNetworkMessage(self):
        return self.packObject(self.room) + self.packObject(self.user)

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos, self.user = self.getObject(message, bytes, pos)


class PrivateRoomOperatorAdded(ServerMessage):
    """ Server code: 145 """
    """ The server send us this message when we're given operator abilities
    in a private room. """
    def __init__(self, room=None):
        self.room = room

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)


class PrivateRoomOperatorRemoved(ServerMessage):
    """ Server code: 146 """
    """ The server send us this message when our operator abilities are removed
    in a private room. """
    def __init__(self, room=None):
        self.room = room

    def makeNetworkMessage(self):
        return self.packObject(self.room)

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)


class LeaveRoom(ServerMessage):
    """ Server code: 15 """
    """ We send this to the server when we want to leave a room. """
    def __init__(self, room=None):
        self.room = room

    def makeNetworkMessage(self):
        return self.packObject(self.room)

    def parseNetworkMessage(self, message):
        self.room = self.getObject(message, bytes)[1]


class UserJoinedRoom(ServerMessage):
    """ Server code: 16 """
    """ The server tells us someone has just joined a room we're in. """
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
    """ Server code: 17 """
    """ The server tells us someone has just left a room we're in. """
    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos, self.username = self.getObject(message, bytes, pos)


class RoomTickerState(ServerMessage):
    """ Server code: 113 """
    """ The server returns a list of tickers in a chat room.

    Tickers are customizable, user-specific messages that appear in a
    banner at the top of a chat room. """
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
    """ Server code: 114 """
    """ The server sends us a new ticker that was added to a chat room.

    Tickers are customizable, user-specific messages that appear in a
    banner at the top of a chat room. """
    def __init__(self):
        self.room = None
        self.user = None
        self.msg = None

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos, self.user = self.getObject(message, bytes, pos)
        pos, self.msg = self.getObject(message, bytes, pos)


class RoomTickerRemove(ServerMessage):
    """ Server code: 115 """
    """ The server informs us that a ticker was removed from a chat room.

    Tickers are customizable, user-specific messages that appear in a
    banner at the top of a chat room. """
    def __init__(self, room=None):
        self.user = None
        self.room = room

    def parseNetworkMessage(self, message):
        pos, self.room = self.getObject(message, bytes)
        pos, self.user = self.getObject(message, bytes, pos)


class RoomTickerSet(ServerMessage):
    """ Server code: 116 """
    """ We send this to the server when we change our own ticker in
    a chat room.

    Tickers are customizable, user-specific messages that appear in a
    banner at the top of a chat room. """
    def __init__(self, room=None, msg=""):
        self.room = room
        self.msg = msg

    def makeNetworkMessage(self):
        return self.packObject(self.room) + self.packObject(self.msg)


class ConnectToPeer(ServerMessage):
    """ Server code: 18 """
    """ Either we ask server to tell someone else we want to establish a
    connection with them, or server tells us someone wants to connect with us.
    Used when the side that wants a connection can't establish it, and tries
    to go the other way around (direct connection has failed).
    """
    def __init__(self, token=None, user=None, type=None):
        self.token = token
        self.user = user
        self.type = type

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
            pos, self.privileged = pos + 1, message[pos]


class MessageUser(ServerMessage):
    """ Server code: 22 """
    """ Chat phrase sent to someone or received by us in private. """
    def __init__(self, user=None, msg=None):
        self.user = user
        self.msg = msg

    def makeNetworkMessage(self):
        return self.packObject(self.user) + self.packObject(self.msg)

    def parseNetworkMessage(self, message):
        pos, self.msgid = self.getObject(message, int)
        pos, self.timestamp = self.getObject(message, int, pos)
        pos, self.user = self.getObject(message, bytes, pos)
        pos, self.msg = self.getObject(message, bytes, pos)


class MessageAcked(ServerMessage):
    """ Server code: 23 """
    """ We send this to the server to confirm that we received a private message.
    If we don't send it, the server will keep sending the chat phrase to us.
    """
    def __init__(self, msgid=None):
        self.msgid = msgid

    def makeNetworkMessage(self):
        return self.packObject(NetworkIntType(self.msgid))


class FileSearch(ServerMessage):
    """ Server code: 26 """
    """ We send this to the server when we search for something. Alternatively,
    the server sends this message to tell us that someone is searching for something.

    The search id is a random number generated by the client and is used to track the
    search results.
    """
    def __init__(self, requestid=None, text=None):
        self.searchid = requestid
        self.searchterm = text
        if text:
            self.searchterm = ' '.join([x for x in text.split() if x != '-'])

    def makeNetworkMessage(self):
        return self.packObject(NetworkIntType(self.searchid)) + self.packObject(self.searchterm)

    def parseNetworkMessage(self, message):
        pos, self.user = self.getObject(message, bytes)
        pos, self.searchid = self.getObject(message, int, pos)
        pos, self.searchterm = self.getObject(message, bytes, pos)


class WishlistSearch(FileSearch):
    """ Server code: 103 """
    pass


class QueuedDownloads(ServerMessage):
    """ Server code: 40 """
    """ The server sends this to indicate if someone has download slots available
    or not. DEPRECIATED """
    def parseNetworkMessage(self, message):
        pos, self.user = self.getObject(message, bytes)
        pos, self.slotsfull = self.getObject(message, int, pos)


class SendSpeed(ServerMessage):
    """ Server code: 34 """
    """ We used to send this after a finished download to let the server update
    the speed statistics for a user. DEPRECIATED """
    def __init__(self, user=None, speed=None):
        self.user = user
        self.speed = speed

    def makeNetworkMessage(self):
        return self.packObject(self.user) + self.packObject(NetworkIntType(self.speed))


class SendUploadSpeed(ServerMessage):
    """ Server code: 121 """
    """ We send this after a finished upload to let the server update the speed
    statistics for ourselves. """
    def __init__(self, speed=None):
        self.speed = speed

    def makeNetworkMessage(self):
        return self.packObject(NetworkIntType(self.speed))


class SharedFoldersFiles(ServerMessage):
    """ Server code: 35 """
    """ We send this to server to indicate the number of folder and files
    that we share. """
    def __init__(self, folders=None, files=None):
        self.folders = folders
        self.files = files

    def makeNetworkMessage(self):
        return self.packObject(NetworkIntType(self.folders)) + self.packObject(NetworkIntType(self.files))


class GetUserStats(ServerMessage):
    """ Server code: 36 """
    """ The server sends this to indicate a change in a user's statistics. """
    def __init__(self, user=None):
        self.user = user
        self.country = None

    def makeNetworkMessage(self):
        return self.packObject(self.user)

    def parseNetworkMessage(self, message):
        pos, self.user = self.getObject(message, bytes)
        pos, self.avgspeed = self.getObject(message, int, pos, getsignedint=1)
        pos, self.downloadnum = self.getObject(message, NetworkLongLongType, pos)
        pos, self.files = self.getObject(message, int, pos)
        pos, self.dirs = self.getObject(message, int, pos)


class Relogged(ServerMessage):
    """ Server code: 41 """
    """ The server sends this if someone else logged in under our nickname,
    and then disconnects us. """
    def parseNetworkMessage(self, message):
        pass


class PlaceInLineResponse(ServerMessage):
    """ Server code: 60 """
    """ Server sends this to indicate change in place in queue while we're
    waiting for files from other peer. DEPRECIATED """
    def __init__(self, user=None, req=None, place=None):
        self.req = req
        self.user = user
        self.place = place

    def makeNetworkMessage(self):
        return self.packObject(self.user) + self.packObject(NetworkIntType(self.req)) + self.packObject(NetworkIntType(self.place))

    def parseNetworkMessage(self, message):
        pos, self.user = self.getObject(message, bytes)
        pos, self.req = self.getObject(message, int, pos)
        pos, self.place = self.getObject(message, int, pos)


class RoomAdded(ServerMessage):
    """ Server code: 62 """
    """ The server tells us a new room has been added. """
    def parseNetworkMessage(self, message):
        self.room = self.getObject(message, bytes)[1]


class RoomRemoved(ServerMessage):
    """ Server code: 63 """
    """ The server tells us a room has been removed. """
    def parseNetworkMessage(self, message):
        self.room = self.getObject(message, bytes)[1]


class RoomList(ServerMessage):
    """ Server code: 64 """
    """ The server tells us a list of rooms and the number of users in
    them. Soulseek has a room size requirement of about 50 users when
    first connecting. Refreshing the list will download all rooms. """
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
    """ Server code: 65 """
    """ Someone is searching for a file with an exact name. DEPRECIATED
    (no results even with official client) """
    def parseNetworkMessage(self, message):
        pos, self.user = self.getObject(message, bytes)
        pos, self.req = self.getObject(message, int, pos)
        pos, self.file = self.getObject(message, bytes, pos)
        pos, self.folder = self.getObject(message, bytes, pos)
        pos, self.size = self.getObject(message, NetworkLongLongType, pos)
        pos, self.checksum = self.getObject(message, int, pos)


class AdminMessage(ServerMessage):
    """ Server code: 66 """
    """ A global message from the server admin has arrived. """
    def parseNetworkMessage(self, message):
        self.msg = self.getObject(message, bytes)[1]


class GlobalUserList(JoinRoom):
    """ Server code: 67 """
    """ We send this to get a global list of all users online. DEPRECIATED """
    def makeNetworkMessage(self):
        return b""

    def parseNetworkMessage(self, message):
        pos, self.users = self.getUsers(message)


class TunneledMessage(ServerMessage):
    """ Server code: 68 """
    """ DEPRECIATED """
    def __init__(self, user=None, req=None, code=None, msg=None):
        self.user = user
        self.req = req
        self.code = code
        self.msg = msg

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
    """ Server code: 83 """
    """ UNUSED """
    def parseNetworkMessage(self, message):
        pos, self.num = self.getObject(message, int)


class ParentSpeedRatio(ParentMinSpeed):
    """ Server code: 84 """
    """ UNUSED """
    def parseNetworkMessage(self, message):
        pos, self.num = self.getObject(message, int)


class SearchParent(ServerMessage):
    """ Server code: 73 """
    """ We send the IP address of our parent to the server. """
    def __init__(self, parentip=None):
        self.parentip = parentip

    def makeNetworkMessage(self):
        import socket
        ip = socket.inet_aton(self.strunreverse(self.parentip))
        return self.packObject(ip)


class ParentInactivityTimeout(ServerMessage):
    """ Server code: 86 """
    """ DEPRECIATED """
    def parseNetworkMessage(self, message):
        pos, self.seconds = self.getObject(message, int)


class SearchInactivityTimeout(ServerMessage):
    """ Server code: 87 """
    """ DEPRECIATED """
    def parseNetworkMessage(self, message):
        pos, self.seconds = self.getObject(message, int)


class MinParentsInCache(ServerMessage):
    """ Server code: 88 """
    """ DEPRECIATED """
    def parseNetworkMessage(self, message):
        pos, self.num = self.getObject(message, int)


class UploadQueueNotification(PeerMessage):
    """ Peer code: 52 """
    def __init__(self, conn):
        self.conn = conn

    def makeNetworkMessage(self):
        return b""

    def parseNetworkMessage(self, message):
        return b""


class DistribAliveInterval(ServerMessage):
    """ Server code: 90 """
    """ DEPRECIATED """
    def parseNetworkMessage(self, message):
        pos, self.seconds = self.getObject(message, int)


class WishlistInterval(ServerMessage):
    """ Server code: 104 """
    def parseNetworkMessage(self, message):
        pos, self.seconds = self.getObject(message, int)


class PrivilegedUsers(ServerMessage):
    """ Server code: 69 """
    """ The server sends us a list of privileged users, a.k.a. users who
    have donated. """
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
    """ Server code: 92 """
    """ We ask the server how much time we have left of our privileges.
    The server responds with the remaining time, in seconds. """
    def makeNetworkMessage(self):
        return b""

    def parseNetworkMessage(self, message):
        pos, self.seconds = self.getObject(message, int)


class AddToPrivileged(ServerMessage):
    """ Server code: 91 """
    """ The server sends us the username of a new privileged user, which we
    add to our list of global privileged users. """
    def parseNetworkMessage(self, message):
        l2, self.user = self.getObject(message, bytes)


class CantConnectToPeer(ServerMessage):
    """ Message 1001 """
    """ We send this to say we can't connect to peer after it has asked us
    to connect. We receive this if we asked peer to connect and it can't do
    this. This message means a connection can't be established either way.
    """
    def __init__(self, token=None, user=None):
        self.token = token
        self.user = user

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
    """ Server code: 32 """
    """ We test if the server responds. """
    def makeNetworkMessage(self):
        return b""

    def parseNetworkMessage(self, message):
        pass


class AddThingILike(ServerMessage):
    """ Server code: 51 """
    """ We send this to the server when we add an item to our likes list. """
    def __init__(self, thing=None):
        self.thing = thing

    def makeNetworkMessage(self):
        return self.packObject(self.thing)


class AddThingIHate(AddThingILike):
    """ Server code: 117 """
    """ We send this to the server when we add an item to our hate list. """
    pass


class RemoveThingILike(ServerMessage):
    """ Server code: 52 """
    """ We send this to the server when we remove an item from our likes list. """
    def __init__(self, thing=None):
        self.thing = thing

    def makeNetworkMessage(self):
        return self.packObject(self.thing)


class RemoveThingIHate(RemoveThingILike):
    """ Server code: 118 """
    """ We send this to the server when we remove an item from our hate list. """
    pass


class UserInterests(ServerMessage):
    """ Server code: 57 """
    """ We ask the server for a user's liked and hated interests. The server
    responds with a list of interests. """
    def __init__(self, user=None):
        self.user = user
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
    """ Server code: 56 """
    """ The server sends us a list of global recommendations and a number
    for each. """
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
    """ Server code: 54 """
    """ The server sends us a list of personal recommendations and a number
    for each. """
    pass


class ItemRecommendations(GlobalRecommendations):
    """ Server code: 111 """
    """ The server sends us a list of recommendations related to a specific
    item, which is usually present in the like/dislike list or an existing
    recommendation list. """
    def __init__(self, thing=None):
        GlobalRecommendations.__init__(self)
        self.thing = thing

    def makeNetworkMessage(self):
        return self.packObject(self.thing)

    def parseNetworkMessage(self, message):
        pos, self.thing = self.getObject(message, bytes)
        self.unpack_recommendations(message, pos)


class SimilarUsers(ServerMessage):
    """ Server code: 110 """
    """ The server sends us a list of similar users related to our interests. """
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
    """ Server code: 112 """
    """ The server sends us a list of similar users related to a specific item,
    which is usually present in the like/dislike list or recommendation list. """
    def __init__(self, thing=None):
        self.thing = thing
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
    """ Server code: 120 """
    def __init__(self, room=None, requestid=None, text=""):
        self.room = room
        self.searchid = requestid
        self.searchterm = ' '.join([x for x in text.split() if x != '-'])

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
    """ Server code: 42 """
    """ We send this to the server when we search a specific user's shares.
    The ticket/search id is a random number generated by the client and is
    used to track the search results. """
    def __init__(self, user=None, requestid=None, text=None):
        self.suser = user
        self.searchid = requestid
        self.searchterm = text

    def makeNetworkMessage(self):
        return (self.packObject(self.suser) +
                self.packObject(NetworkIntType(self.searchid)) +
                self.packObject(self.searchterm))

    def parseNetworkMessage(self, message):
        pos, self.user = self.getObject(message, bytes)
        pos, self.searchid = self.getObject(message, int, pos)
        pos, self.searchterm = self.getObject(message, bytes, pos)


class PierceFireWall(PeerMessage):
    """ This is the very first message sent by the peer that established a
    connection, if it has been asked by the other peer to do so. The token
    is taken from the ConnectToPeer server message. """
    def __init__(self, conn, token=None):
        self.conn = conn
        self.token = token

    def makeNetworkMessage(self):
        return self.packObject(NetworkIntType(self.token))

    def parseNetworkMessage(self, message):
        pos, self.token = self.getObject(message, int)


class PeerInit(PeerMessage):
    """ This message is sent by the peer that initiated a connection,
    not necessarily a peer that actually established it. Token apparently
    can be anything. Type is 'P' if it's anything but filetransfer,
    'F' otherwise. """
    def __init__(self, conn, user=None, type=None, token=None):
        self.conn = conn
        self.user = user
        self.type = type
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
        self.user = user
        self.msg = msg

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
    """ Peer code: 15 """
    """ We ask the other peer to send us their user information, picture
    and all."""
    def __init__(self, conn):
        self.conn = conn

    def makeNetworkMessage(self):
        return b""

    def parseNetworkMessage(self, message):
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

    def parseNetworkMessage(self, message):
        pos, self.descr = self.getObject(message, bytes)
        pos, self.has_pic = pos + 1, message[pos]
        if self.has_pic:
            pos, self.pic = self.getObject(message, bytes, pos, 0, 0, True, True)  # Raw bytes
        pos, self.totalupl = self.getObject(message, int, pos)
        pos, self.queuesize = self.getObject(message, int, pos)
        pos, self.slotsavail = pos + 1, message[pos]

        if len(message[pos:]) >= 4:
            pos, self.uploadallowed = self.getObject(message, int, pos)

    def makeNetworkMessage(self):
        if self.pic is not None:
            pic = bytes([1]) + self.packObject(self.pic)
        else:
            pic = bytes([0])

        return (self.packObject(self.descr) +
                pic +
                self.packObject(NetworkIntType(self.totalupl)) +
                self.packObject(NetworkIntType(self.queuesize)) +
                bytes([self.slotsavail]) +
                self.packObject(NetworkIntType(self.uploadallowed)))


class SharedFileList(PeerMessage):
    """ Peer code: 5 """
    """ A peer responds with a list of shared files when we've sent
    a GetSharedFileList. """
    def __init__(self, conn, shares=None):
        self.conn = conn
        self.list = shares
        self.built = None

    def parseNetworkMessage(self, message, nozlib=False):
        try:
            if not nozlib:
                message = zlib.decompress(message)

            self._parseNetworkMessage(message)
        except Exception as error:
            log.addwarning(_("Exception during parsing %(area)s: %(exception)s") % {'area': 'SharedFileList', 'exception': error})
            self.list = {}

    def _parseNetworkMessage(self, message):
        shares = []
        pos, ndir = self.getObject(message, int)
        for i in range(ndir):
            pos, directory = self.getObject(message, bytes, pos)
            pos, nfiles = self.getObject(message, int, pos)
            files = []
            for j in range(nfiles):
                pos, code = pos + 1, message[pos]
                pos, name = self.getObject(message, bytes, pos)
                pos, size = self.getObject(message, NetworkLongLongType, pos, getsignedint=True, printerror=False)
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
        msg = msg + self.packObject(len(self.list))
        for (key, value) in self.list.items():
            msg = msg + self.packObject(key.replace(os.sep, "\\")) + value
        if not nozlib:
            self.built = zlib.compress(msg)
        else:
            self.built = msg
        return self.built


class GetSharedFileList(PeerMessage):
    """ Peer code: 4 """
    """ We send this to a peer to ask for a list of shared files. """
    def __init__(self, conn):
        self.conn = conn

    def makeNetworkMessage(self):
        return b""

    def parseNetworkMessage(self, message):
        pass


class FileSearchRequest(PeerMessage):
    """ Peer code: 8 """
    """ We send this to the peer when we search for a file.
    Alternatively, the peer sends this to tell us it is
    searching for a file. """
    def __init__(self, conn, requestid=None, text=None):
        self.conn = conn
        self.requestid = requestid
        self.text = text

    def makeNetworkMessage(self):
        return self.packObject(NetworkIntType(self.requestid)) + self.packObject(self.text)

    def parseNetworkMessage(self, message):
        pos, self.searchid = self.getObject(message, int)
        pos, self.searchterm = self.getObject(message, bytes, pos)


class FileSearchResult(PeerMessage):
    """ Peer code: 9 """
    """ The peer sends this when it has a file search match. The
    token/ticket is taken from original FileSearchRequest message. """
    def __init__(self, conn, user=None, geoip=None, token=None, shares=None, fileindex=None, freeulslots=None, ulspeed=None, inqueue=None, fifoqueue=None):
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
        try:
            message = zlib.decompress(message)
            self._parseNetworkMessage(message)
        except Exception as error:
            log.addwarning(_("Exception during parsing %(area)s: %(exception)s") % {'area': 'FileSearchResult', 'exception': error})
            self.list = {}

    def _parseNetworkMessage(self, message):
        self.pos, self.user = self.getObject(message, bytes)
        self.pos, self.token = self.getObject(message, int, self.pos)
        self.pos, nfiles = self.getObject(message, int, self.pos)
        shares = []
        for i in range(nfiles):
            self.pos, code = self.pos + 1, message[self.pos]
            self.pos, name = self.getObject(message, bytes, self.pos)
            # suppressing errors with unpacking, can be caused by incorrect sizetype
            self.pos, size = self.getObject(message, NetworkLongLongType, self.pos, printerror=False)
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
            msg += (bytes([1]) +
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
        msg += (bytes([self.freeulslots]) +
                self.packObject(NetworkIntType(self.ulspeed)) +
                self.packObject(NetworkIntType(queuesize)))
        return zlib.compress(msg)


class FolderContentsRequest(PeerMessage):
    """ Peer code: 36 """
    """ We ask the peer to send us the contents of a single folder. """
    def __init__(self, conn, directory=None):
        self.conn = conn
        self.dir = directory

    def makeNetworkMessage(self):
        return self.packObject(1) + self.packObject(self.dir)

    def parseNetworkMessage(self, message):
        pos, self.something = self.getObject(message, int)
        pos, self.dir = self.getObject(message, bytes, pos)


class FolderContentsResponse(PeerMessage):
    """ Peer code: 37 """
    """ A peer responds with the contents of a particular folder
    (with all subfolders) when we've sent a FolderContentsRequest. """
    def __init__(self, conn, directory=None, shares=None):
        self.conn = conn
        self.dir = directory
        self.list = shares

    def parseNetworkMessage(self, message):
        try:
            message = zlib.decompress(message)
            self._parseNetworkMessage(message)
        except Exception as error:
            log.addwarning(_("Exception during parsing %(area)s: %(exception)s") % {'area': 'FolderContentsResponse', 'exception': error})
            self.list = {}

    def _parseNetworkMessage(self, message):
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
                    pos, size = self.getObject(message, NetworkLongLongType, pos, getsignedint=1, printerror=False)
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
            msg = msg + bytes([1]) + self.packObject(i[0]) + self.packObject(i[1]) + self.packObject(0)
            if i[2] is None:
                msg = msg + self.packObject('') + self.packObject(0)
            else:
                msg = msg + self.packObject("mp3") + self.packObject(3)
                msg = msg + self.packObject(0) + self.packObject(i[2][0]) + self.packObject(1) + self.packObject(i[3]) + self.packObject(2) + self.packObject(i[2][1])
        return zlib.compress(msg)


class TransferRequest(PeerMessage):
    """ Peer code: 40 """
    """ We request a file from a peer, or tell a peer that we want to send
    a file to them. """
    def __init__(self, conn, direction=None, req=None, file=None, filesize=None, realfile=None):
        self.conn = conn
        self.direction = direction
        self.req = req
        self.file = file  # virtual file
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
    """ Peer code: 41 """
    """ Response to TransferRequest - either we (or the other peer) agrees,
    or tells the reason for rejecting the file transfer. """
    def __init__(self, conn, allowed=None, reason=None, req=None, filesize=None):
        self.conn = conn
        self.allowed = allowed
        self.req = req
        self.reason = reason
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
        if message[pos:]:
            if self.allowed:
                pos, self.filesize = self.getObject(message, int, pos)
            else:
                pos, self.reason = self.getObject(message, bytes, pos)


class PlaceholdUpload(PeerMessage):
    """ Peer code: 42 """
    """ DEPRECIATED """
    def __init__(self, conn, file=None):
        self.conn = conn
        self.file = file

    def makeNetworkMessage(self):
        return self.packObject(self.file)

    def parseNetworkMessage(self, message):
        pos, self.file = self.getObject(message, bytes)


class QueueUpload(PlaceholdUpload):
    """ Peer code: 43 """
    pass


class UploadFailed(PlaceholdUpload):
    """ Peer code: 46 """
    pass


class PlaceInQueue(PeerMessage):
    """ Peer code: 44 """
    def __init__(self, conn, filename=None, place=None):
        self.conn = conn
        self.filename = filename
        self.place = place

    def makeNetworkMessage(self):
        return self.packObject(self.filename) + self.packObject(NetworkIntType(self.place))

    def parseNetworkMessage(self, message):
        pos, self.filename = self.getObject(message, bytes)
        pos, self.place = self.getObject(message, int, pos)


class PlaceInQueueRequest(PlaceholdUpload):
    """ Peer code: 51 """
    pass


class QueueFailed(PeerMessage):
    """ Peer code: 50 """
    def __init__(self, conn, file=None, reason=None):
        self.conn = conn
        self.file = file
        self.reason = reason

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
        self.req = req

    def makeNetworkMessage(self):
        msg = self.packObject(self.req)
        return msg


class HaveNoParent(ServerMessage):
    """ Server code: 71 """
    def __init__(self, noparent=None):
        self.noparent = noparent

    def makeNetworkMessage(self):
        return bytes((self.noparent,))


class DistribAlive(DistribMessage):
    """ Distrib code: 0 """
    def __init__(self, conn):
        self.conn = conn

    def parseNetworkMessage(self, message):
        pass


class DistribSearch(DistribMessage):
    """ Distrib code: 3 """
    """
    Search request that arrives through the distributed network.
    We transmit the search request to our children.

    Search requests are sent to us by the server using SearchRequest
    if we're a branch root, or by our parent using DistribSearch.
    (TODO: check that this works / is implemented)
    """
    def __init__(self, conn):
        self.conn = conn

    def parseNetworkMessage(self, message):
        try:
            self._parseNetworkMessage(message)
        except Exception as error:
            log.addwarning(_("Exception during parsing %(area)s: %(exception)s") % {'area': 'DistribSearch', 'exception': error})
            return False

    def _parseNetworkMessage(self, message):
        pos, self.unknown = self.getObject(message, int, printerror=False)
        pos, self.user = self.getObject(message, bytes, pos, printerror=False)
        pos, self.searchid = self.getObject(message, int, pos, printerror=False)
        pos, self.searchterm = self.getObject(message, bytes, pos, printerror=False)


class DistribServerSearch(DistribMessage):
    """ Distrib code: 93 """
    """
    Search request that arrives through the distributed network.
    We transmit the search request to our children.

    Search requests are sent to us by the server using SearchRequest
    if we're a branch root, or by our parent using DistribSearch.
    (TODO: check that this works / is implemented)
    """
    def __init__(self, conn):
        self.conn = conn

    def parseNetworkMessage(self, message):
        try:
            self._parseNetworkMessage(message)
        except Exception as error:
            log.addwarning(_("Exception during parsing %(area)s: %(exception)s") % {'area': 'DistribServerSearch', 'exception': error})
            return False

    def _parseNetworkMessage(self, message):
        pos, self.unknown = self.getObject(message, NetworkLongLongType, printerror=False)
        pos, self.user = self.getObject(message, bytes, pos, printerror=False)
        pos, self.searchid = self.getObject(message, int, pos, printerror=False)
        pos, self.searchterm = self.getObject(message, bytes, pos, printerror=False)


class DistribBranchLevel(DistribMessage):
    """ Distrib code: 4 """
    """ TODO: implement fully """
    def __init__(self, conn):
        self.conn = conn

    def parseNetworkMessage(self, message):
        pos, self.value = self.getObject(message, int)
        # print message.__repr__()


class DistribBranchRoot(DistribMessage):
    """ Distrib code: 5 """
    """ TODO: implement fully """
    def __init__(self, conn):
        self.conn = conn

    def parseNetworkMessage(self, message):
        # pos, self.value = self.getObject(message, types.IntType)
        pos, self.user = self.getObject(message, bytes)
        # print self.something, self.user


class DistribChildDepth(DistribMessage):
    """ Distrib code: 7 """
    """ TODO: implement fully """
    def __init__(self, conn):
        self.conn = conn

    def parseNetworkMessage(self, message):
        pos, self.value = self.getObject(message, int)
        # print self.something, self.user


class BranchLevel(ServerMessage):
    """ Server code: 126 """
    """ TODO: implement fully """
    def parseNetworkMessage(self, message):
        pos, self.value = self.getObject(message, int)
        # print message.__repr__()


class BranchRoot(ServerMessage):
    """ Server code: 127 """
    """ TODO: implement fully """
    def parseNetworkMessage(self, message):
        # pos, self.value = self.getObject(message, types.IntType)
        pos, self.user = self.getObject(message, bytes)
        # print self.something, self.user


class AcceptChildren(ServerMessage):
    """ Server code: 100 """
    """ We tell the server if we want to accept child nodes.
    TODO: actually use this somewhere """
    def __init__(self, enabled=None):
        self.enabled = enabled

    def makeNetworkMessage(self):
        return bytes([self.enabled])


class ChildDepth(ServerMessage):
    """ Server code: 129 """
    """ TODO: implement fully """
    def parseNetworkMessage(self, message):
        pos, self.value = self.getObject(message, int)


class NetInfo(ServerMessage):
    """ Server code: 102 """
    """ The server send us information about what nodes have been
    added/removed in the network. """
    def parseNetworkMessage(self, message: bytes):
        self.list = {}
        pos, num = self.getObject(message, int)
        for i in range(num):
            pos, username = self.getObject(message, bytes, pos)
            pos, self.ip = pos + 4, socket.inet_ntoa(message[pos:pos + 4][::-1])
            pos, port = self.getObject(message, int, pos)
            self.list[username] = (self.ip, port)


class SearchRequest(ServerMessage):
    """ Server code: 93 """
    """ The server sends us search requests from other users. """
    def parseNetworkMessage(self, message):
        pos, self.code = 1, message[0]
        pos, self.something = self.getObject(message, int, pos)
        pos, self.user = self.getObject(message, bytes, pos)
        pos, self.searchid = self.getObject(message, int, pos)
        pos, self.searchterm = self.getObject(message, bytes, pos)


class UserPrivileged(ServerMessage):
    """ Server code: 122 """
    """ We ask the server whether a user is privileged or not. """
    def __init__(self, user=None):
        self.user = user
        self.privileged = None

    def makeNetworkMessage(self):
        return self.packObject(self.user)

    def parseNetworkMessage(self, message):
        pos, self.user = self.getObject(message, bytes, 0)  # noqa: F821
        pos, self.privileged = pos + 1, bool(message[pos])


class GivePrivileges(ServerMessage):
    """ Server code: 123 """
    """ We give (part of) our privileges, specified in days, to another
    user on the network. """
    def __init__(self, user=None, days=None):
        self.user = user
        self.days = days

    def makeNetworkMessage(self):
        return self.packObject(self.user) + self.packObject(self.days)


class PopupMessage:
    """For messages that should be shown to the user prominently, for example
    through a popup. Should be used sparsely."""
    def __init__(self, title, message):
        self.title = title
        self.message = message
